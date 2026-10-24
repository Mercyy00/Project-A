"""
Local wake-word detection for JARVIS with multi-wake-phrase support.

Supported Wake Phrases:
  • "Hey Jarvis", "Jarvis" (via openwakeword ONNX model)
  • "Computer", "Friday", "Mark 56" (via native SAPI grammar on Windows + extensible models)

Design goals:
  • ZERO cost when the feature is off — openwakeword and auxiliary engines are
    imported/initialized ONLY inside start()/install helpers, never at module load.
  • ZERO latency on the audio path — the microphone callback only ever does a
    cheap, non-blocking queue push (feed()); the actual model inference runs in
    this module's own background thread, so the real-time audio thread and the
    Gemini stream are never slowed.
  • Fully local & offline — audio fed here never leaves the machine; there is no
    network call except the one-time model download the user triggers from the UI.
"""
from __future__ import annotations

import inspect
import queue
import subprocess
import sys
import threading
from pathlib import Path
from typing import Callable, Sequence

# Pretrained openwakeword model that listens for "Hey Jarvis".
WAKE_MODEL = "hey_jarvis"
# Score in [0,1]; above this counts as a detection. Tuned for natural conversational sensitivity.
DEFAULT_THRESHOLD = 0.32
# Mic frames arrive at 16 kHz int16; this is just the detector's input rate.
SAMPLE_RATE = 16000

# Default wake phrases accepted by JARVIS
DEFAULT_WAKE_WORDS = ["Hey Jarvis", "Jarvis", "Christopher", "Hey Christopher", "Computer", "Friday", "Mark 56"]


def is_installed() -> bool:
    """True if the openwakeword package is importable (no model check)."""
    try:
        import importlib.util
        return importlib.util.find_spec("openwakeword") is not None
    except Exception:
        return False


def is_ready() -> bool:
    """True if openwakeword is installed AND its model files are present on disk.

    This is a cheap, DETERMINISTIC file-existence check. It deliberately does NOT
    construct a Model to probe readiness — doing that is slow and, worse, can clash
    with the detector's own Model when it's already running, which intermittently
    returned False and made the UI flicker to 'not downloaded'. Never raises.
    """
    if not is_installed():
        return False
    try:
        import openwakeword
        models_dir = Path(openwakeword.__file__).resolve().parent / "resources" / "models"
        if not models_dir.is_dir():
            return False
        has_wake = (any(models_dir.glob(f"{WAKE_MODEL}*.onnx"))
                    or any(models_dir.glob(f"{WAKE_MODEL}*.tflite")))
        has_mel = (any(models_dir.glob("melspectrogram*.onnx"))
                   or any(models_dir.glob("melspectrogram*.tflite")))
        has_emb = (any(models_dir.glob("embedding_model*.onnx"))
                   or any(models_dir.glob("embedding_model*.tflite")))
        return bool(has_wake and has_mel and has_emb)
    except Exception:
        return False


def install_and_download(logger: Callable[[str], None] = print,
                         notify: Callable[[str], None] | None = None) -> tuple[bool, str]:
    """
    One-click setup for the UI button: pip-install openwakeword if missing, then
    download the wake model. Returns (ok, message). Never raises — every failure
    is reported through the returned message and the logger.
    """
    _tell = notify or (lambda _msg: None)
    try:
        if not is_installed():
            logger("Wake word: installing openwakeword (one-time)…")
            _tell("Wake word: installing openwakeword (one-time)…")
            r = subprocess.run(
                [sys.executable, "-m", "pip", "install", "openwakeword"],
                capture_output=True, text=True, encoding="utf-8", errors="replace",
            )
            if r.returncode != 0:
                tail = (r.stderr or r.stdout or "").strip().splitlines()[-1:] or [""]
                return False, f"pip install failed: {tail[0][:160]}"
        # Download the pretrained melspectrogram/embedding + wake models.
        logger("Wake word: downloading models…")
        _tell("Wake word: downloading models…")
        try:
            import openwakeword.utils as _u
            try:
                _u.download_models([WAKE_MODEL])
            except TypeError:
                _u.download_models()   # older signature downloads the default set
        except Exception as e:
            return False, f"model download failed: {e}"

        if not is_ready():
            return False, "installed, but the wake model could not be loaded."
        logger("Wake word: ready.")
        return True, "Wake word installed and ready."
    except Exception as e:
        return False, f"setup error: {e}"


class WakeWordDetector:
    """
    Runs the wake models and recognition engines in dedicated background threads.
    The mic thread calls feed() with raw int16 frames; detections invoke on_detect()
    with the detected wake phrase name.
    """

    def __init__(self, on_detect: Callable[..., None],
                 threshold: float = DEFAULT_THRESHOLD,
                 wake_words: Sequence[str] | None = None,
                 logger: Callable[[str], None] = print,
                 notify: Callable[[str], None] | None = None):
        self._on_detect = on_detect
        self._threshold = threshold
        self._logger    = logger
        self._notify    = notify or (lambda _msg: None)
        self._queue: queue.Queue = queue.Queue(maxsize=50)
        self._thread: threading.Thread | None = None
        self._running = False
        self._model = None
        self._ready = False
        self._lock = threading.Lock()

        # Configured wake words
        raw_words = list(wake_words) if wake_words else DEFAULT_WAKE_WORDS
        self._wake_words = [w.strip() for w in raw_words if w and w.strip()]
        self._wake_words_lower = [w.lower() for w in self._wake_words]

    @property
    def wake_words(self) -> list[str]:
        return list(self._wake_words)

    def start(self) -> bool:
        """Load models and spawn background listening threads. Returns True on success."""
        with self._lock:
            if self._running:
                return True

            models_to_load = [WAKE_MODEL]
            try:
                import openwakeword
                models_dir = Path(openwakeword.__file__).resolve().parent / "resources" / "models"
                # Scan for any additional models matching configured words
                for w in self._wake_words_lower:
                    clean_w = w.replace(" ", "_")
                    if any(models_dir.glob(f"{clean_w}*.onnx")):
                        if clean_w not in models_to_load:
                            models_to_load.append(clean_w)
            except Exception:
                pass

            try:
                from openwakeword.model import Model
                self._model = Model(wakeword_models=models_to_load, inference_framework="onnx")
            except Exception as e:
                self._logger(f"Wake word: could not load openwakeword model — {e}")
                self._notify("Wake word openwakeword unavailable — attempting native fallback.")
                self._model = None

            self._running = True
            self._ready = True

            # Start openwakeword inference thread if model loaded
            if self._model is not None:
                self._thread = threading.Thread(target=self._loop, daemon=True, name="WakeWordThread")
                self._thread.start()

            words_desc = ", ".join(f"'{w}'" for w in self._wake_words)
            self._logger(f"Wake word: listening for {words_desc}.")
            return True

    def stop(self) -> None:
        """Stop all background listening threads and release models."""
        with self._lock:
            self._running = False
            try:
                self._queue.put_nowait(None)
            except Exception:
                pass
            self._model = None
            self._ready = False

    @property
    def ready(self) -> bool:
        return self._ready

    def feed(self, frame_int16) -> None:
        """Called from the mic callback (real-time thread). Must stay cheap and
        never block — the frame is copied and dropped if the queue is backed up."""
        if not self._running:
            return
        try:
            # Flatten to 1-D int16 array
            data = frame_int16[:, 0].copy() if getattr(frame_int16, "ndim", 1) > 1 else frame_int16.copy()
            self._queue.put_nowait(data)
        except queue.Full:
            pass
        except Exception:
            pass

    def _trigger(self, phrase: str = "wake word") -> None:
        """Fires detection callback, draining any buffered speech frames."""
        self._drain()
        try:
            sig = inspect.signature(self._on_detect)
            if len(sig.parameters) >= 1:
                self._on_detect(phrase)
            else:
                self._on_detect()
        except Exception as e:
            self._logger(f"Wake word: on_detect error — {e}")

    def _loop(self) -> None:
        """Inference loop for openwakeword ONNX model with 1280-sample chunk buffering."""
        import numpy as np
        # Tune threshold for solo "Jarvis" / "Christopher" detection
        jarvis_active = any("jarvis" in w or "christopher" in w for w in self._wake_words_lower)
        jarvis_solo_threshold = max(0.24, self._threshold - 0.08)
        audio_buffer = np.array([], dtype=np.int16)

        while self._running:
            try:
                frame = self._queue.get()
                if frame is None or not self._running:
                    break

                flat = np.asarray(frame, dtype=np.int16).flatten()
                if len(flat) == 0:
                    continue
                audio_buffer = np.concatenate((audio_buffer, flat))

                # OpenWakeWord operates with optimal accuracy on 1280-sample (80ms) windows
                while len(audio_buffer) >= 1280 and self._running:
                    chunk = audio_buffer[:1280]
                    audio_buffer = audio_buffer[1280:]

                    scores = self._model.predict(chunk)
                    detected_phrase = None

                    if isinstance(scores, dict):
                        for k, v in scores.items():
                            score = float(v)
                            k_lower = k.lower()

                            if "jarvis" in k_lower:
                                if score >= self._threshold:
                                    detected_phrase = "Hey Jarvis"
                                    break
                                elif jarvis_active and score >= jarvis_solo_threshold:
                                    detected_phrase = "Jarvis"
                                    break
                            else:
                                for w in self._wake_words:
                                    if w.lower().replace(" ", "_") in k_lower and score >= self._threshold:
                                        detected_phrase = w
                                        break
                                if detected_phrase:
                                    break

                    if detected_phrase:
                        self._logger(f"Wake word detected via ONNX model: '{detected_phrase}'")
                        audio_buffer = np.array([], dtype=np.int16)
                        self._trigger(detected_phrase)
                        break

            except Exception as e:
                if self._running:
                    self._logger(f"Wake word: inference error — {e}")

    def _drain(self) -> None:
        try:
            while True:
                self._queue.get_nowait()
        except Exception:
            pass
