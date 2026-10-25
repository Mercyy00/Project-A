# Project A handoff

## User goal

Make Project A work reliably. Use Gemini as the only LLM provider, reduce waste against a free Gemini quota, and make the voice match `D:\engineers\JAY\JARVIS\Mark-LVI` (the Mark-LVI app uses Gemini Live `gemini-3.1-flash-live-preview` with the `Charon` voice). The user also called out core behavior, tools, messaging, voice, and vision as areas that need review and repair.

## Current working state

- Branch: `codex/gemini-only-mark-voice`
- Changes are uncommitted and present in the working tree.
- Do not read, print, or write real `.env` secrets. `.env.example` is safe to edit.
- The user explicitly authorized work across modules. Do not modify `ARCHITECTURE.md` or `tools/base.py` without team consensus.

## Changes already made

- Removed Groq from the core chat, vision fallback, and creator outline fallback paths; Gemini is now the only configured LLM provider.
- Set Flash-Lite as the default text model and made quota/429 errors stop without retrying other models. Availability failures may try a model fallback.
- Updated the default text model to the currently documented stable `gemini-3.5-flash-lite` model; the project still honors an explicit `GEMINI_MODEL` override.
- Reduced text-turn tool schema overhead by selecting only intent-relevant tools. Normal chat sends no tool declarations; tests cover screen, web, document, messaging, and memory categories.
- Removed the UI server's startup `ping` generation and its independent second Gemini request after a core failure.
- Changed Gemini key validation to fetch model metadata instead of generating a test response.
- Reduced the default chat history window from 20 to 8 entries and rebuilds the SDK session with only retained turns.
- Wired `python main.py --voice` to Gemini Live with the Mark-LVI `Charon` voice. It now defaults to stable `gemini-3.8-live`, with `gemini-3.1-flash-live-preview` as a compatibility fallback.
- Removed the HUD's browser speech-synthesis fallback, which could select a different system voice when neural playback failed.
- Corrected the HUD speech language labels, added Marathi selection, removed fake Piper/System options that silently ran Edge, and rejects unknown TTS engine names.
- Fixed the HUD English default label/voice mismatch (India/Prabhat) and updated the stranded screen tool model default.
- Added `pypdf` to project dependencies and installed it in this environment because existing PDF tests require it.
- Sandboxed the ElevenLabs settings integration test so it no longer writes its dummy key to `.env`. The earlier unsandboxed test had persisted its known dummy key and an `elevenlabs` setting; those exact artifacts were removed/reset without displaying key values. If a real ElevenLabs key was present before that test, the test may have overwritten it; it cannot be restored from this workspace. The Gemini key was not touched.
- Updated provider UI, docs, dependency list, and tests to match Gemini-only configuration.

## Latest fixes

- Wired the HUD voice button to one persistent Gemini Live session using Mark-LVI's default `Charon` voice. Live transcription now uses the `en-IN` language hint and the custom vocabulary term `JARVIS`, improving recognition of the user's Indian-English accent and assistant name. Session status and transcripts flow back to the HUD, and stopping the voice session cancels its microphone/audio tasks.
- Added a 12-second timeout to each Gemini Live WebSocket handshake. If every Live model is unavailable, the HUD now receives a readable error and exits the connecting state rather than hanging indefinitely. The timeout is configurable with `LIVE_CONNECT_TIMEOUT_SECONDS`.
- Changed the HUD to start Gemini Live automatically when its WebSocket comes online, using one persistent session across utterances. Live server-side VAD waits 750 ms of silence before finalizing a turn, and the existing interruption handler discards JARVIS audio as soon as the user speaks. A short Charon greeting plays once when the session first connects.
- Fixed the built-in polished-PDF prompt (`Create a polished PDF about the latest ...`) so it routes directly to document creation without first spending a Gemini chat request. Current-fact snippets remain DDGS-based, and the creator's local outline fallback can still render a real PDF if Gemini quota is exhausted. Regression coverage verifies the file begins with `%PDF`.
- Improved `search_web`: DDGS sessions are closed correctly, result count is capped at eight, snippet/title/URL lengths are bounded, search failures are reported instead of silently discarded, and the selected browser search still opens. Search uses no Gemini call, preserving quota. Search results are explicitly treated as untrusted data.
- Added a one-time HUD startup greeting when the WebSocket first comes online. It uses the existing no-Gemini TTS path and does not repeat on reconnect.
- Compared Mark-LVI messaging: its `plugins/_whatsapp_core.py` driver is absent from the shared reference folder. Project A keeps its saved-contact checks and confirmation gate; its WhatsApp dispatch still uses pywhatkit and does not provide Mark's claimed visual verification.

## Verification

- Focused suite after the latest changes: the relevant UI, PDF, Downloads, Gemini, and streaming tests passed (`10 passed` in the combined focused run, plus a separate PDF wording test).
- Full suite on the current tree: `424 passed, 6 subtests passed`.
- `git diff --check` passed.
- No live Gemini requests were made, so model access, free-tier quota behavior, and actual audio playback still need a manual check with the user's own key and devices.
- After the Live hang was reported, added the 12-second per-model connection timeout, tested that a stalled handshake cleans up and reports an error to the HUD, restarted the verified Project A server process, and confirmed `/health` returns HTTP 200 with the database connected.
- API-key screenshot follow-up: the exact “Error connecting to validation service.” message is absent from current `ui/index.html`, which indicates the screen is likely from stale cached UI. Bumped the PWA cache to `jarvis-pwa-v6` and made navigation requests network-first. The currently running local server responds healthy; `/api/config/key-status` and `/sw.js` both respond, and key status reports configured without exposing the key. No key was submitted to Google. The running Python server is not in reload mode, so restart JARVIS to load backend Python edits; reload the app to get the new service worker.
- Fixed request cross-talk by serializing access to the shared Gemini conversation session. WebSocket text replies now stream into the HUD as tokens arrive; the UI still speaks the completed response once.
- Normalized “open my Downloads folder” into the local Explorer route and broadened direct PDF creation parsing to support “create a PDF for me about …”. Added regression coverage for both.
- Fixed plain-`and` browser action parsing. For the user's CarryMinati/YouTube → Chrome → new tab/LinkedIn → new tab/search-it-up example, JARVIS now issues separate ordered browser actions; “it” refers to the last named search (LinkedIn). The UI no longer lets its Chrome shortcut consume the complete multi-action sentence as one search query.
- Improved Indian-English voice input: browser recognition already uses `en-IN`; it now asks for up to three transcript alternatives and prefers one that correctly captures the JARVIS wake word. The local Whisper fallback receives the selected language (`en`, `hi`, or `mr`) instead of relying on language autodetection alone.
- The running app had a stale `GEMINI_MODEL=gemini-3.5-flash` setting. Updated only the non-secret `GEMINI_MODEL` entry in `.env` to `gemini-3.5-flash-lite`, restarted the local server, and confirmed the status endpoint reports the new model. UI key configuration tests: `5 passed`.

## Important remaining work

1. Review whether all dormant `voice/providers/` OpenAI-compatible adapters should remain available. The active core LLM is Gemini-only; these adapters are part of a separate modular pipeline.
- The HUD voice button now runs the same Gemini Live `Charon` voice as Mark-LVI. Typed chat autoplay still uses the configured local/Edge neural TTS (`en-IN-PrabhatNeural` by default) so it does not spend another Gemini request. If the user expects every typed reply to use Charon too, that needs a separate design choice because Charon is part of the Live session.
- Check Mark-LVI's full voice interaction behavior against Project A's Live engine, especially function-call handling, reconnect/resumption, microphone/speaker errors, and user-facing failures.
- No live Gemini request or device-level audio playback was tested; verify Live connection, greeting audio, and a few Indian-English commands manually with the user's own key and devices when quota is available.
- Restart JARVIS to load backend Python changes, reload the desktop app, then verify a real Gemini response, a Downloads open, PDF output, and the user's multi-search prompt. Do not paste or log the user's key.
- Project A's WhatsApp tool is safer than Mark-LVI's missing-driver fallback, but pywhatkit cannot prove delivery. A verified transport integration remains separate work.

## Notes on quota diagnosis

Google's Gemini quota is applied per project and varies by model and tier. The local changes remove redundant calls and shorten retained history; they cannot increase Google-side free-tier limits. Check AI Studio's project/model limits if the app still receives 429s after these fixes.
