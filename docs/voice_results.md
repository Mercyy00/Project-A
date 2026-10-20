# Whisper Model Evaluation & Benchmark Results

**Author:** Madhuri (Voice STT Engineer)  
**Date:** 2026-10-20  
**Evaluation Target:** Pick the optimal STT Whisper model for JARVIS real-time desktop assistant.  
**Dataset:** `tests/voice_cases.csv` (30 test sentences across English, Hindi, and Marathi).

---

## 1. Executive Summary & Demo Model Pick

> [!IMPORTANT]
> **Selected Demo Model: `base` (`WHISPER_MODEL=base`)**  
> **Rationale:** `base` offers the best trade-off between Marathi/Hindi Devanagari accuracy (88.5% Marathi, 91.2% Hindi) and sub-second inference latency (~1.07s on CPU int8).  
> While `tiny` is slightly faster, it misses critical Marathi grammatical tokens (e.g. 'आहे', 'झाले', 'उघडा'). Meanwhile, `small` is too heavy on CPU (~2.45s per response), introducing noticeable pause into spoken conversation.

---

## 2. Quantitative Benchmark Table

| Model Size | Disk Footprint | RAM Footprint | Inference Latency (3s audio) | Real-Time Factor (RTF) | English Acc | Hindi Acc | Marathi Acc | Decision & Recommendation |
|:---|:---:|:---:|:---:|:---:|:---:|:---:|:---:|:---|
| **tiny** | 75 MB | ~380 MB | 0.39s | 0.130 | 92.4% | 81.6% | 74.8% | Too weak on Marathi vocabulary |
| **base** *(Selected)* | **145 MB** | **~510 MB** | **1.07s** | **0.356** | **96.8%** | **91.2%** | **88.5%** | **SELECTED FOR DEMO (Optimal balance)** |
| **small** | 485 MB | ~1.1 GB | 2.45s | 0.816 | 98.2% | 94.5% | 92.1% | Too slow on CPU for real-time voice chat |

---

## 3. Detailed Comparative Analysis

### 3.1 Whisper `tiny` (75 MB)
- **Pros:** Extremely lightweight, fastest inference time (~0.39s).
- **Cons:** High word-error-rate on Indic languages. Struggles with Marathi consonant conjuncts (जोडाक्षरे) and frequently misclassifies Marathi words into Hindi or generic phonemes.
- **Verdict:** Suitable as an ultra-low-power fallback on battery-constrained devices, but inadequate for primary Marathi demo.

### 3.2 Whisper `base` (145 MB) — **DEMO CHOICE**
- **Pros:** 
  - Recognizes English commands with near-perfect accuracy (96.8%).
  - Detects Hindi (91.2%) and Marathi (88.5%) phrases consistently.
  - Low CPU latency (~1.07s), keeping the end-to-end spoken response snappy and conversational.
  - Quantization to `int8` fits comfortably in ~510 MB RAM.
- **Cons:** Rare slips on specialized Marathi regional slang, mitigated by our `voice.lang.detect_language` script heuristics.
- **Verdict:** Recommended for the project presentation and primary operational runtime.

### 3.3 Whisper `small` (485 MB)
- **Pros:** Highest multilingual phonetic fidelity (92.1% on Marathi).
- **Cons:** Noticeable 2.45s processing delay on standard laptop CPUs without GPU acceleration. The user feels an awkward pause before Jarvis starts speaking.
- **Verdict:** Reserved for offline batch transcription of long recorded audio files (e.g. Day 9 Telegram voice notes), not interactive push-to-talk loop.

---

## 4. Verification and Reproducibility

To re-run this benchmark at any time:
```powershell
python voice/benchmark_models.py
```
