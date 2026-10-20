# JARVIS Voice Module (STT, TTS & Multilingual Voice Loop)

**Owner / Engineers:** Madhuri (Voice STT) + Akanksha (Voice TTS) with Pair A (Jayesh)  
**Deliverables Completed:** Days 1 through 6 from *JARVIS 8-Member Catch-Up Plan (v2)*  
**Workspace:** `D:\Project A`

---

## Deliverables Roadmap & Progress (Days 1 – 6)

| Day | Feature / Deliverable | Key Files | Done When / Verification Criteria | Status |
|:---:|---|---|---|:---:|
| **Day 1** | Audio check, microphone enumeration, 16 kHz mono check, device-busy handling | `voice/audio_check.py` | 3-second recording plays back through speakers | **DONE** |
| **Day 2** | STT with faster-whisper, 16 kHz mono capture, `transcribe_mic` | `voice/stt.py`, `voice/test_stt.py` | Say *"Jarvis what is the date today?"* and receive text | **DONE** |
| **Day 3** | Hindi & Marathi STT, language detection (`'en'`, `'hi'`, `'mr'`), 30 test sentences | `voice/lang.py`, `tests/voice_cases.csv` | All 30 test sentences pass with 100% precision | **DONE** |
| **Day 4** | Auto-stop `listen()` on ~1.5s silence; multilingual personality phrases | `voice/stt.py`, `voice/lang.py` | `listen()` stops by itself; voice sounds natural | **DONE** |
| **Day 5** | Benchmark Whisper `tiny` / `base` / `small`; generate report; pick demo model | `voice/benchmark_models.py`, `docs/voice_results.md` | Quantitative report exists; `base` selected for demo | **DONE** |
| **Day 6** | `main_voice.py` spoken loop: push-to-talk, `listen -> brain -> speak`, latency measurement | `main_voice.py`, `core/brain.py`, `voice/tts.py` | Talk to Jarvis and hear him answer in user's language | **DONE** |

---

## Project Structure

```
D:\Project A\
│
├── venv\                    # Dedicated Python 3.12 Virtual Environment
├── requirements.txt         # All core, voice STT, and voice TTS dependencies
├── .env                     # WHISPER_MODEL=base, WHISPER_DEVICE=cpu, WHISPER_COMPUTE_TYPE=int8
├── .env.example             # Configuration template
├── main_voice.py            # [Day 6] Full spoken loop (listen -> brain -> speak)
│
├── run_jarvis_voice.bat     # [Day 6] Launch spoken conversation with 1 click
├── run_benchmark.bat        # [Day 5] Run Whisper model benchmark
├── run_voice_tests.bat      # [Day 3] Run 30 multilingual unit tests
├── run_audio_check.bat      # [Day 1] Microphone & speaker loopback test
├── run_live_mic_test.bat    # [Day 2/3] Live speech recognition test
│
├── core\
│   └── brain.py             # [Day 6] JarvisBrain with multilingual persona (EN/HI/MR)
│
├── voice\
│   ├── __init__.py          # Package exports (Transcriber, speak, listen, detect_language)
│   ├── audio_check.py       # [Day 1] 16 kHz mono mic test & playback
│   ├── stt.py               # [Day 2-4] faster-whisper STT with silence-based listen()
│   ├── lang.py              # [Day 3-4] Language detection and personality phrases
│   ├── tts.py               # [Day 6] JarvisSpeaker with edge-tts & pyttsx3 fallback
│   ├── test_stt.py          # STT unit tests (11 tests, 30 cases)
│   ├── test_tts.py          # TTS unit tests & audio demo
│   └── benchmark_models.py  # [Day 5] Benchmark suite for tiny/base/small
│
├── tests\
│   └── voice_cases.csv      # 30 benchmark sentences (10 English, 10 Hindi, 10 Marathi)
│
└── docs\
    └── voice_results.md     # [Day 5] Model benchmark report & decision rationale
```

---

## 1-Click Verification Scripts

Simply double-click any `.bat` file in `D:\Project A`:
- **`run_jarvis_voice.bat`**: Starts the live spoken assistant. Speak in English, Hindi, or Marathi and Jarvis replies aloud.
- **`run_benchmark.bat`**: Measures Whisper model latency, RAM, and accuracy, updating `docs/voice_results.md`.
- **`run_voice_tests.bat`**: Executes the 30-case language detection test suite.
- **`run_audio_check.bat`**: Records 3 seconds of audio and plays it back to verify hardware.
