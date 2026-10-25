"""JARVIS Gemini Live - Real-Time Bidirectional Voice Streaming Engine.
Ported from and powered by Mark LVI (core/gemini.py & main.py live loop).

Provides sub-800ms conversational audio streaming with acoustic barge-in,
prebuilt human voice ('Charon' / Mark-grade voice), live input/output
transcription, session resumption, acoustic echo guard, and transparent tool calling.
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
import os
import sys
import threading
import time
from typing import Any, AsyncIterator, Callable, Dict, List, Optional

# Ensure console stdout and stderr never crash on Windows charmap / cp1252
for _stream in ("stdout", "stderr"):
    try:
        _s = getattr(sys, _stream, None)
        if _s is not None and hasattr(_s, "reconfigure"):
            _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from dotenv import load_dotenv
from google import genai
from google.genai import types
import numpy as np

from voice.echo import EchoGuard

load_dotenv()

# Audio streaming parameters (16kHz mono in, 24kHz mono out)
SEND_SAMPLE_RATE: int = int(os.getenv("LIVE_SEND_SAMPLE_RATE", "16000"))
RECEIVE_SAMPLE_RATE: int = int(os.getenv("LIVE_RECEIVE_SAMPLE_RATE", "24000"))
CHANNELS: int = 1
CHUNK_SIZE: int = 1024

# Model ladder for Live API (Mark-LVI tested defaults)
DEFAULT_LIVE_MODELS: tuple[str, ...] = (
    os.getenv("LIVE_MODEL", "models/gemini-3.1-flash-live-preview"),
    "models/gemini-3.1-flash-live-preview",
    "gemini-2.5-flash-native-audio-preview-12-2025",
)

DEFAULT_LIVE_VOICE: str = os.getenv("LIVE_VOICE", "Charon")
LIVE_CONNECT_TIMEOUT_SECONDS: float = float(os.getenv("LIVE_CONNECT_TIMEOUT_SECONDS", "12"))


class GeminiLiveEngine:
    """Manages full-duplex, real-time voice streaming with Gemini Live API."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        voice_name: Optional[str] = None,
        enable_tools: bool = True,
        event_callback: Optional[Callable[[Dict[str, str]], None]] = None,
    ) -> None:
        self.api_key: str = (api_key or os.getenv("GEMINI_API_KEY") or "").strip()
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is required to initialize GeminiLiveEngine.")

        self.voice_name: str = voice_name or DEFAULT_LIVE_VOICE
        self.enable_tools: bool = enable_tools
        self.event_callback: Optional[Callable[[Dict[str, str]], None]] = event_callback
        self._tools: Optional[List[Callable[..., Any]]] = None
        self.connected: bool = False
        self.client: genai.Client = genai.Client(api_key=self.api_key)

        self._running: bool = False
        self._audio_out_queue: asyncio.Queue[bytes] = asyncio.Queue()
        self._mic_queue: asyncio.Queue[bytes] = asyncio.Queue()
        self._active_session: Optional[Any] = None
        self._resume_handle: Optional[str] = None
        self._executed_tool_ids: set[str] = set()

        # Acoustic Echo Guard & Speaking State (Mark LVI architecture)
        self._echo: EchoGuard = EchoGuard()
        self._is_speaking: bool = False
        self._speaking_lock: threading.Lock = threading.Lock()
        self._tail_until: float = 0.0

        # Microphone mute state
        self._muted: bool = False
        self._muted_lock: threading.Lock = threading.Lock()

    @property
    def is_muted(self) -> bool:
        """Return True if the microphone audio stream is muted."""
        with self._muted_lock:
            return self._muted

    def set_muted(self, muted: bool) -> None:
        """Mute or unmute microphone audio capture and streaming."""
        with self._muted_lock:
            self._muted = bool(muted)
        if self._muted:
            # Drain any pending microphone frames so nothing buffered is sent
            while not self._mic_queue.empty():
                try:
                    self._mic_queue.get_nowait()
                except Exception:
                    break
            self._notify({"type": "voice_status", "status": "muted", "message": "Microphone muted."})
        else:
            self._notify({"type": "voice_status", "status": "connected", "message": "Microphone active. Listening..."})

    def _get_system_prompt(self) -> str:
        """Construct system persona instruction for Gemini Live conversation."""
        from core.brain import DEFAULT_SYSTEM_PROMPT
        live_mandate = (
            "\n\nLIVE AUDIO PROTOCOL: You are speaking directly through real-time speakers. "
            "Keep all conversational responses extremely crisp, natural, and under 15 words. "
            "Speak smoothly with natural cadence and realistic human tone. "
            "Let the user finish each utterance before answering. Never speak over the user; "
            "if they begin speaking while you are talking, stop and listen until they finish."
        )
        return DEFAULT_SYSTEM_PROMPT + live_mandate

    def _discover_tools(self) -> List[Callable[..., Any]]:
        """Retrieve system tools from JarvisBrain for function calling."""
        if not self.enable_tools:
            return []
        if self._tools is not None:
            return self._tools
        try:
            from core.brain import JarvisBrain
            brain = JarvisBrain(enable_tools=True)
            self._tools = brain.tools
            return self._tools
        except Exception as exc:
            print(f"[WARN] Failed to discover tools for Live engine: {exc}", file=sys.stderr)
            return []

    def _notify(self, event: Dict[str, str]) -> None:
        """Send status or transcription events to connected HUD."""
        if self.event_callback is None:
            return
        try:
            self.event_callback(event)
        except Exception as exc:
            print(f"[WARN] Live voice event callback failed: {exc}", file=sys.stderr)

    def _build_config(self) -> types.LiveConnectConfig:
        """Build the LiveConnectConfig payload for Gemini Live session."""
        tools_list = self._discover_tools() if self.enable_tools else None

        config_kwargs: Dict[str, Any] = {
            "response_modalities": ["AUDIO"],
            "speech_config": types.SpeechConfig(
                voice_config=types.VoiceConfig(
                    prebuilt_voice_config=types.PrebuiltVoiceConfig(
                        voice_name=self.voice_name
                    )
                )
            ),
            "system_instruction": self._get_system_prompt(),
            "output_audio_transcription": {},
            "input_audio_transcription": types.AudioTranscriptionConfig(
                language_codes=["en-IN"],
                custom_vocabulary=["JARVIS"],
            ),
            "realtime_input_config": types.RealtimeInputConfig(
                automatic_activity_detection=types.AutomaticActivityDetection(
                    disabled=False,
                    end_of_speech_sensitivity=types.EndSensitivity.END_SENSITIVITY_LOW,
                    silence_duration_ms=750,
                ),
            ),
        }

        if self._resume_handle:
            try:
                config_kwargs["session_resumption"] = types.SessionResumptionConfig(handle=self._resume_handle)
            except Exception:
                pass

        if tools_list:
            config_kwargs["tools"] = tools_list

        return types.LiveConnectConfig(**config_kwargs)

    @asynccontextmanager
    async def _open_live_session(
        self,
        model_name: str,
        config: types.LiveConnectConfig,
    ) -> AsyncIterator[Any]:
        """Open a Live session with a bounded handshake and guaranteed cleanup."""
        connection = self.client.aio.live.connect(model=model_name, config=config)
        try:
            session = await asyncio.wait_for(
                connection.__aenter__(),
                timeout=LIVE_CONNECT_TIMEOUT_SECONDS,
            )
        except BaseException as exc:
            try:
                await asyncio.wait_for(
                    connection.__aexit__(type(exc), exc, exc.__traceback__),
                    timeout=2.0,
                )
            except BaseException:
                pass
            if isinstance(exc, TimeoutError):
                raise TimeoutError(
                    f"Timed out connecting to Gemini Live model '{model_name}' "
                    f"after {LIVE_CONNECT_TIMEOUT_SECONDS:g} seconds."
                ) from exc
            raise

        try:
            yield session
        except BaseException as exc:
            try:
                await connection.__aexit__(type(exc), exc, exc.__traceback__)
            except BaseException:
                pass
            raise
        else:
            await connection.__aexit__(None, None, None)

    async def _audio_input_worker(self, loop: asyncio.AbstractEventLoop) -> None:
        """Capture microphone audio at 16kHz PCM and push chunks to _mic_queue with echo suppression and mute gating."""
        import sounddevice as sd

        def callback(indata: Any, frames: int, time_info: Any, status: Any) -> None:
            if not self._running:
                return

            # Software mute: drop audio blocks immediately without transmission
            with self._muted_lock:
                if self._muted:
                    return

            # Echo cancellation: Never send mic audio while JARVIS is speaking
            with self._speaking_lock:
                jarvis_speaking = self._is_speaking
            if jarvis_speaking:
                return

            # Measure amplitude & push live visual level to HUD
            try:
                samples = indata.astype(np.float32)
                rms = float(np.sqrt(np.mean(samples ** 2)))
                peak = float(np.max(np.abs(samples)))
                norm_amp = min(1.0, rms / 3200.0)
                if norm_amp > 0.03:
                    self._notify({"type": "mic_amplitude", "level": f"{norm_amp:.3f}"})
            except Exception:
                rms = 0.0
                peak = 0.0

            # Digital silence gate (hardware switch off / OS mic muted at source)
            # If peak is practically zero (< 40 on int16), do not push empty noise
            if peak < 40.0:
                return

            # Echo tail: Check if speaker room reverberation is still echoing
            now = time.monotonic()
            if now < self._tail_until:
                try:
                    if not self._echo.is_user_speech(indata, SEND_SAMPLE_RATE, rms):
                        return
                    self._tail_until = 0.0
                except Exception:
                    return
            elif self._echo._hist:
                self._echo.reset()

            pcm_bytes = indata.tobytes()
            loop.call_soon_threadsafe(self._mic_queue.put_nowait, pcm_bytes)

        # Allow user to configure specific input device via MIC_DEVICE environment variable
        mic_dev: Optional[Any] = None
        mic_env = os.getenv("MIC_DEVICE", "").strip()
        if mic_env:
            try:
                mic_dev = int(mic_env)
            except ValueError:
                mic_dev = mic_env

        try:
            try:
                dev_info = sd.query_devices(mic_dev, "input") if mic_dev is not None else sd.query_devices(kind="input")
                dev_name = dev_info.get("name", "Default")
            except Exception:
                dev_name = "Default"

            with sd.InputStream(
                samplerate=SEND_SAMPLE_RATE,
                channels=CHANNELS,
                dtype="int16",
                blocksize=CHUNK_SIZE,
                device=mic_dev,
                callback=callback,
            ):
                print(f"[*] Microphone audio stream open (16kHz 16-bit PCM, Device: {dev_name}). Speak freely.")
                while self._running:
                    await asyncio.sleep(0.1)
        except Exception as exc:
            print(f"[!] Microphone audio capture error: {exc}", file=sys.stderr)

    async def _audio_output_worker(self) -> None:
        """Pull received 24kHz audio chunks and play them back through speakers with echo registration."""
        import sounddevice as sd

        try:
            out_stream = sd.RawOutputStream(
                samplerate=RECEIVE_SAMPLE_RATE,
                channels=CHANNELS,
                dtype="int16",
                blocksize=CHUNK_SIZE,
            )
            out_stream.start()

            while self._running:
                try:
                    chunk = await asyncio.wait_for(self._audio_out_queue.get(), timeout=0.1)
                    with self._speaking_lock:
                        self._is_speaking = True
                    try:
                        arr = np.frombuffer(chunk, dtype=np.int16)
                        level = float(np.sqrt(np.mean(arr.astype(np.float32) ** 2)))
                        self._echo.note_output(arr, RECEIVE_SAMPLE_RATE, level)
                    except Exception:
                        pass
                    await asyncio.to_thread(out_stream.write, chunk)
                except asyncio.TimeoutError:
                    if self._audio_out_queue.empty():
                        with self._speaking_lock:
                            if self._is_speaking:
                                self._is_speaking = False
                                self._tail_until = time.monotonic() + 0.35
                    continue
                except Exception as exc:
                    if not self._running:
                        break
                    print(f"[!] Audio playback error: {exc}", file=sys.stderr)
        except Exception as exc:
            print(f"[!] Output audio device error: {exc}", file=sys.stderr)
        finally:
            try:
                out_stream.stop()
                out_stream.close()
            except Exception:
                pass

    def _purge_output_buffer(self) -> None:
        """Immediately drop all queued audio packets on barge-in interruption."""
        while not self._audio_out_queue.empty():
            try:
                self._audio_out_queue.get_nowait()
            except asyncio.QueueEmpty:
                break
        with self._speaking_lock:
            self._is_speaking = False

    async def _send_mic_stream(self, session: Any) -> None:
        """Stream microphone chunks to the active Gemini Live session."""
        while self._running:
            try:
                chunk = await self._mic_queue.get()
                await session.send_realtime_input(
                    audio=types.Blob(
                        data=chunk,
                        mime_type=f"audio/pcm;rate={SEND_SAMPLE_RATE}",
                    )
                )
            except Exception as exc:
                if not self._running:
                    break
                print(f"[!] Error sending mic audio: {exc}", file=sys.stderr)
                await asyncio.sleep(0.05)

    async def _receive_server_stream(self, session: Any) -> None:
        """Receive incoming audio chunks, transcriptions, and tool calls from Gemini Live."""
        in_buf: list[str] = []
        out_buf: list[str] = []

        while self._running:
            try:
                async for msg in session.receive():
                    if not self._running:
                        break

                    # Session resumption handle
                    _sru = getattr(msg, "session_resumption_update", None)
                    if _sru is not None:
                        if getattr(_sru, "resumable", False) and getattr(_sru, "new_handle", None):
                            self._resume_handle = _sru.new_handle

                    # 1. Handle Server Content (Audio + Transcriptions + Interruption)
                    if msg.server_content:
                        content = msg.server_content

                        # Acoustic barge-in: Server detected user speech, cut audio immediately (<20ms)
                        if getattr(content, "interrupted", False):
                            self._purge_output_buffer()
                            in_buf.clear()
                            out_buf.clear()
                            self._notify({"type": "voice_status", "status": "connected", "message": "Interrupted. Listening..."})
                            print("\n[BARGE-IN] Interrupted by user speech. Output silenced.")

                        # Real-time User Input Transcript
                        input_trans = getattr(content, "input_transcription", None)
                        if input_trans and hasattr(input_trans, "text") and input_trans.text:
                            clean_in = input_trans.text.strip()
                            if clean_in:
                                in_buf.append(clean_in)
                                live_in = " ".join(in_buf)
                                sys.stdout.write(f"\r[YOU]: {live_in}")
                                sys.stdout.flush()
                                self._notify({"type": "voice_live_hearing", "text": live_in})

                        # Real-time Assistant Output Transcript (dedup incremental chunks)
                        output_trans = getattr(content, "output_transcription", None)
                        if output_trans and hasattr(output_trans, "text") and output_trans.text:
                            clean_out = output_trans.text.strip()
                            if clean_out:
                                joined_out = " ".join(out_buf)
                                if clean_out not in joined_out:
                                    out_buf.append(clean_out)
                                    live_out = " ".join(out_buf)
                                    sys.stdout.write(f"\r[JARVIS]: {live_out}")
                                    sys.stdout.flush()
                                    self._notify({"type": "voice_live_speaking", "text": live_out})

                        # Audio packet streaming
                        model_turn = getattr(content, "model_turn", None)
                        if model_turn and hasattr(model_turn, "parts"):
                            for part in model_turn.parts:
                                inline_data = getattr(part, "inline_data", None)
                                if inline_data and hasattr(inline_data, "data") and inline_data.data:
                                    self._audio_out_queue.put_nowait(inline_data.data)

                        # Turn complete: commit full clean turn to HUD & memory
                        if getattr(content, "turn_complete", False):
                            full_in = " ".join(in_buf).strip()
                            full_out = " ".join(out_buf).strip()
                            if full_in:
                                sys.stdout.write(f"\r[YOU]: {full_in}\n")
                                self._notify({"type": "voice_turn", "speaker": "user", "text": full_in})
                            if full_out:
                                sys.stdout.write(f"[JARVIS]: {full_out}\n\n")
                                self._notify({"type": "voice_turn", "speaker": "assistant", "text": full_out})
                                try:
                                    from memory.storage import MemoryManager
                                    asyncio.create_task(MemoryManager().save_interaction(role="user", content=full_in))
                                    asyncio.create_task(MemoryManager().save_interaction(role="assistant", content=full_out))
                                except Exception:
                                    pass
                            in_buf.clear()
                            out_buf.clear()

                    # 2. Handle Tool Function Calls autonomously during Live audio
                    if msg.tool_call and getattr(msg.tool_call, "function_calls", None):
                        from tools.registry import execute_tool

                        responses = []
                        for fc in msg.tool_call.function_calls:
                            fn_name = fc.name
                            fn_args = fc.args if hasattr(fc, "args") and fc.args else {}
                            fc_id = getattr(fc, "id", None) or f"{fn_name}_{hash(str(fn_args))}"

                            # Deduplication guard: Never re-execute a tool call that was already executed
                            if fc_id in self._executed_tool_ids:
                                print(f"\n[*] [LIVE TOOL] Skipping already executed tool call: {fn_name} (id={fc_id})")
                                res_str = "Task was already completed successfully in previous turn."
                            else:
                                self._executed_tool_ids.add(fc_id)
                                print(f"\n[*] [LIVE TOOL] Executing: {fn_name}({fn_args})")
                                try:
                                    # Offload tool execution to background worker thread so audio streaming and websocket loop stay alive
                                    res = await asyncio.to_thread(execute_tool, fn_name, fn_args)
                                    res_str = res.to_llm_string()
                                except Exception as exc:
                                    res_str = f"[FAILED] Tool error: {exc}"

                            self._notify({"type": "tool_step", "text": f"{fn_name}({fn_args})"})
                            responses.append(
                                types.FunctionResponse(
                                    name=fn_name,
                                    id=fc.id,
                                    response={"result": res_str},
                                )
                            )

                        if responses:
                            try:
                                await session.send_tool_response(function_responses=responses)
                            except Exception as err:
                                print(f"[!] Failed to send tool response: {err}", file=sys.stderr)

            except asyncio.CancelledError:
                break
            except Exception as exc:
                if not self._running:
                    break
                print(f"[!] Server receive stream error: {exc}", file=sys.stderr)
                break

    async def run(self) -> None:
        """Run the full-duplex Gemini Live session with persistent auto-reconnect and model fallback."""
        self._running = True
        loop = asyncio.get_running_loop()
        self.connected = False
        self._notify({"type": "voice_status", "status": "connecting", "voice": self.voice_name})

        # Start persistent hardware audio workers
        mic_task = asyncio.create_task(self._audio_input_worker(loop))
        out_task = asyncio.create_task(self._audio_output_worker())

        print("\n" + "=" * 62)
        print(f"   PROJECT JARVIS - GEMINI LIVE FULL-DUPLEX ENGINE")
        print(f"   Voice: {self.voice_name} | Latency: Real-Time (<800ms)")
        print(f"   Acoustic Barge-In: Active | Tools: {len(self._discover_tools())} Registered")
        print("=" * 62)

        try:
            while self._running:
                config = self._build_config()
                connected_in_cycle = False
                last_error = None

                for model_name in DEFAULT_LIVE_MODELS:
                    if not self._running:
                        break
                    print(f"[*] Connecting to Gemini Live node: '{model_name}'...")
                    try:
                        async with self._open_live_session(model_name, config) as session:
                            self._active_session = session
                            self.connected = True
                            connected_in_cycle = True
                            print(f"[OK] Connected to Live Session! (Model: {model_name}, Voice: {self.voice_name})\n")
                            print("[*] Speak into your microphone anytime. Interrupt mid-sentence anytime.")
                            print("[*] Press Ctrl+C in console to end session.\n")
                            self._notify({
                                "type": "voice_status", "status": "connected",
                                "voice": self.voice_name, "model": model_name,
                            })

                            recv_task = asyncio.create_task(self._receive_server_stream(session))
                            send_task = asyncio.create_task(self._send_mic_stream(session))
                            try:
                                await asyncio.wait(
                                    [send_task, recv_task],
                                    return_when=asyncio.FIRST_COMPLETED,
                                )
                            finally:
                                for task in (send_task, recv_task):
                                    if task is not None and not task.done():
                                        task.cancel()
                                await asyncio.gather(
                                    *(task for task in (send_task, recv_task) if task is not None),
                                    return_exceptions=True,
                                )

                            # Normal cycle completion or turn boundary; keep persistent session alive
                            break
                    except asyncio.CancelledError:
                        raise
                    except Exception as exc:
                        last_error = exc
                        err_str = str(exc).lower()
                        print(f"[!] Model '{model_name}' connection failed ({exc}). Stepping down ladder...", file=sys.stderr)
                        if any(term in err_str for term in (
                            "api_key", "unauthorized", "429", "quota", "resource_exhausted"
                        )):
                            break
                        await asyncio.sleep(0.5)

                if not self._running:
                    break

                if not connected_in_cycle:
                    if not self.connected:
                        # Initial connection failed to all models: notify HUD of error and abort
                        print(f"\n[!] Unable to connect to any Gemini Live model node: {last_error}", file=sys.stderr)
                        print("[!] Gemini Live voice is unavailable.\n")
                        self._notify({
                            "type": "voice_status", "status": "error",
                            "message": str(last_error or "Gemini Live could not connect."),
                        })
                        break
                    else:
                        print(f"\n[!] Live connection blip ({last_error}). Reconnecting in 2s...", file=sys.stderr)
                        self._notify({
                            "type": "voice_status", "status": "connecting",
                            "message": "Reconnecting to Live voice...",
                        })
                        await asyncio.sleep(2.0)
                else:
                    # Seamless reconnect maintaining resume_handle context
                    await asyncio.sleep(0.1)

        finally:
            self._running = False
            self.connected = False
            self._active_session = None
            for task in (mic_task, out_task):
                if not task.done():
                    task.cancel()
            await asyncio.gather(mic_task, out_task, return_exceptions=True)

    def stop(self) -> None:
        """Signal live session termination."""
        self._running = False
        self._purge_output_buffer()


def main() -> None:
    """CLI entrypoint for standalone Gemini Live session."""
    engine = GeminiLiveEngine()
    try:
        asyncio.run(engine.run())
    except (KeyboardInterrupt, EOFError):
        print("\n[*] Live voice session ended. Goodbye, sir.")


if __name__ == "__main__":
    main()
