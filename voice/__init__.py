"""Voice STT and Language processing package for Project JARVIS.

Maintained by Madhuri (Voice STT Engineer).
"""

from voice.lang import (
    SUPPORTED_LANGUAGES,
    detect_language,
    get_language_code,
    get_supported_languages,
)
from voice.stt import (
    AudioFileError,
    MicrophoneError,
    ModelLoadError,
    STTError,
    Transcriber,
    get_transcriber,
    listen,
    transcribe_file,
    transcribe_mic,
)

__all__ = [
    "Transcriber",
    "transcribe_mic",
    "transcribe_file",
    "listen",
    "get_transcriber",
    "STTError",
    "MicrophoneError",
    "ModelLoadError",
    "AudioFileError",
    "detect_language",
    "get_language_code",
    "get_supported_languages",
    "SUPPORTED_LANGUAGES",
]
