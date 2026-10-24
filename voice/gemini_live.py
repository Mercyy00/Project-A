"""JARVIS Gemini Live - Real-Time Bidirectional Voice Streaming Engine.

Provides sub-800ms conversational audio streaming with acoustic barge-in,
prebuilt human voice ('Charon' / Mark-grade voice), live input/output
transcription, and transparent tool calling.
"""

from __future__ import annotations

import asyncio
import os
import sys
import threading
import time
from typing import Any, Callable, Dict, List, Optional

from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

# Audio streaming parameters (16kHz mono in, 24kHz mono out)
SEND_SAMPLE_RATE: int = int(os.getenv("LIVE_SEND_SAMPLE_RATE", "16000"))
RECEIVE_SAMPLE_RATE: int = int(os.getenv("LIVE_RECEIVE_SAMPLE_RATE", "24000"))
CHANNELS: int = 1
CHUNK_SIZE: int = 1024

# Model ladder for Live API
DEFAULT_LIVE_MODELS: tuple[str, ...] = (
    os.getenv("LIVE_MODEL", "models/gemini-2.0-flash-exp"),
    "models/gemini-2.0-flash-exp",
    "gemini-2.0-flash-exp",
    "models/gemini-2.5-flash-native-audio-preview-12-2025",
    "models/gemini-3.1-flash-live-preview",
)

DEFAULT_LIVE_VOICE: str = os.getenv("LIVE_VOICE", "Charon")


class GeminiLiveEngine:
    """Manages full-duplex, real-time voice streaming with Gemini Live API."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        voice_name: Optional[str] = None,
        enable_tools: bool = True,
    ) -> None:
        """Initialize the Gemini Live engine.

        Args:
            api_key: Gemini API key (defaults to GEMINI_API_KEY from environment).
            voice_name: Prebuilt voice name ('Charon', 'Puck', 'Fenrir', 'Aoede', 'Kore').
            enable_tools: Whether to expose registered system tools to the session.
        """
        self.api_key: str = (api_key or os.getenv("GEMINI_API_KEY") or "").strip()
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is required to initialize GeminiLiveEngine.")

        self.voice_name: str = voice_name or DEFAULT_LIVE_VOICE
        self.enable_tools: bool = enable_tools
        self.client: genai.Client = genai.Client(api_key=self.api_key)

        self._running: bool = False
        self._audio_out_queue: asyncio.Queue[bytes] = asyncio.Queue()
        self._mic_queue: asyncio.Queue[bytes] = asyncio.Queue()
        self._active_session: Optional[Any] = None

    def _get_system_prompt(self) -> str:
        """Construct system persona instruction for Gemini Live conversation."""
        from core.brain import DEFAULT_SYSTEM_PROMPT
        live_mandate = (
            "\n\nLIVE AUDIO PROTOCOL: You are speaking directly through real-time speakers. "
            "Keep all conversational responses extremely crisp, natural, and under 15 words. "
            "Speak smoothly with natural cadence and realistic human tone."
        )
        return DEFAULT_SYSTEM_PROMPT + live_mandate

    def _discover_tools(self) -> List[Callable[..., Any]]:
        """Retrieve system tools from JarvisBrain for function calling."""
        if not self.enable_tools:
            return []
        try:
            from core.brain import JarvisBrain
            brain = JarvisBrain(enable_tools=True)
            return brain.tools
        except Exception as exc:
            print(f"[WARN] Failed to discover tools for Live engine: {exc}", file=sys.stderr)
            return []

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
            "input_audio_transcription": {},
        }

        if tools_list:
            config_kwargs["tools"] = tools_list

        return types.LiveConnectConfig(**config_kwargs)

    async def _audio_input_worker(self, loop: asyncio.AbstractEventLoop) -> None:
        """Capture microphone audio at 16kHz PCM and push chunks to _mic_queue."""
        import sounddevice as sd

        def callback(indata: Any, frames: int, time_info: Any, status: Any) -> None:
            if not self._running:
                return
            pcm_bytes = indata.tobytes()
            loop.call_soon_threadsafe(self._mic_queue.put_nowait, pcm_bytes)

        try:
            with sd.InputStream(
                samplerate=SEND_SAMPLE_RATE,
                channels=CHANNELS,
                dtype="int16",
                blocksize=CHUNK_SIZE,
                callback=callback,
            ):
                print("[*] 🎤 Microphone audio stream open (16kHz 16-bit PCM). Speak freely.")
                while self._running:
                    await asyncio.sleep(0.1)
        except Exception as exc:
            print(f"[!] Microphone audio capture error: {exc}", file=sys.stderr)

    async def _audio_output_worker(self) -> None:
        """Pull received 24kHz audio chunks and play them back through speakers."""
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
                    await asyncio.to_thread(out_stream.write, chunk)
                except asyncio.TimeoutError:
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
        async for msg in session.receive():
            if not self._running:
                break

            # 1. Handle Server Content (Audio + Transcriptions + Interruption)
            if msg.server_content:
                content = msg.server_content

                # Acoustic barge-in: Server detected user speech, cut audio immediately (<20ms)
                if getattr(content, "interrupted", False):
                    self._purge_output_buffer()
                    print("\n[⚡ BARGE-IN] Interrupted by user speech. Output silenced.")

                # Real-time User Input Transcript
                input_trans = getattr(content, "input_transcription", None)
                if input_trans and hasattr(input_trans, "text") and input_trans.text:
                    sys.stdout.write(f"\r[YOU]: {input_trans.text}")
                    sys.stdout.flush()

                # Real-time Assistant Output Transcript
                output_trans = getattr(content, "output_transcription", None)
                if output_trans and hasattr(output_trans, "text") and output_trans.text:
                    sys.stdout.write(output_trans.text)
                    sys.stdout.flush()

                # Audio packet streaming
                model_turn = getattr(content, "model_turn", None)
                if model_turn and hasattr(model_turn, "parts"):
                    for part in model_turn.parts:
                        inline_data = getattr(part, "inline_data", None)
                        if inline_data and hasattr(inline_data, "data") and inline_data.data:
                            self._audio_out_queue.put_nowait(inline_data.data)

            # 2. Handle Tool Function Calls autonomously during Live audio
            if msg.tool_call and getattr(msg.tool_call, "function_calls", None):
                from tools.registry import execute_tool

                responses = []
                for fc in msg.tool_call.function_calls:
                    fn_name = fc.name
                    fn_args = fc.args if hasattr(fc, "args") and fc.args else {}
                    print(f"\n[*] ⚙️ [LIVE TOOL] Executing: {fn_name}({fn_args})")
                    try:
                        res = execute_tool(fn_name, fn_args)
                        res_str = res.to_llm_string()
                    except Exception as exc:
                        res_str = f"[FAILED] Tool error: {exc}"

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

    async def run(self) -> None:
        """Run the full-duplex live session with automatic model ladder fallback."""
        config = self._build_config()
        self._running = True
        loop = asyncio.get_running_loop()

        # Start background hardware audio workers
        mic_task = asyncio.create_task(self._audio_input_worker(loop))
        out_task = asyncio.create_task(self._audio_output_worker())

        connected = False
        last_error = None

        print("\n" + "=" * 62)
        print(f"   PROJECT JARVIS - GEMINI LIVE FULL-DUPLEX ENGINE")
        print(f"   Voice: {self.voice_name} | Latency: Real-Time (<800ms)")
        print(f"   Acoustic Barge-In: Active | Tools: {len(self._discover_tools())} Registered")
        print("=" * 62)

        for model_name in DEFAULT_LIVE_MODELS:
            print(f"[*] Connecting to Gemini Live node: '{model_name}'...")
            try:
                async with self.client.aio.live.connect(model=model_name, config=config) as session:
                    self._active_session = session
                    connected = True
                    print(f"[✓] Connected to Live Session! (Model: {model_name}, Voice: {self.voice_name})\n")
                    print("[*] Speak into your microphone anytime. Interrupt mid-sentence anytime.")
                    print("[*] Press Ctrl+C in console to end session.\n")

                    send_task = asyncio.create_task(self._send_mic_stream(session))
                    recv_task = asyncio.create_task(self._receive_server_stream(session))

                    done, pending = await asyncio.wait(
                        [send_task, recv_task],
                        return_when=asyncio.FIRST_EXCEPTION,
                    )
                    for task in pending:
                        task.cancel()

                    break
            except Exception as exc:
                last_error = exc
                err_str = str(exc).lower()
                print(f"[!] Model '{model_name}' connection failed ({exc}). Stepping down ladder...", file=sys.stderr)
                if "api_key" in err_str or "unauthorized" in err_str:
                    break
                await asyncio.sleep(0.5)

        self._running = False
        mic_task.cancel()
        out_task.cancel()

        if not connected:
            print(f"\n[!] Unable to connect to any Gemini Live model node: {last_error}", file=sys.stderr)
            print("[!] Falling back to standard turn-based voice loop.\n")
            from main_voice import main as fallback_main
            fallback_main()

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
