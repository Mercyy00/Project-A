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
- Built full YouTube automation and playback control suite via `YouTubeControlTool` in `tools/youtube_tool.py`:
  - **Direct Video Playback**: Scrapes YouTube search results to extract clean video IDs and immediately streams/plays the top matching video (watch URL) rather than just opening a search results list.
  - **Scroll Navigation**: Scrolls YouTube page down and up smoothly (`scroll_down`, `scroll_up`) with target window focusing.
  - **Click & Open Video**: Opens specific video by index from search results or clicks the video card on screen (`click_video`).
  - **Playback Controls**: Pauses (`pause`), resumes (`resume`), and toggles play/pause with YouTube's universal `'k'` hotkey.
  - **Fullscreen & Out Fullscreen**: Enters fullscreen (`fullscreen`) and exits fullscreen (`exit_fullscreen`) via `'f'` / `Esc`.
  - **Full Media Control**: Mute/unmute (`'m'`), volume up/down (`Up`/`Down`), skip forward 10s (`'l'`), rewind 10s (`'j'`), next/prev video (`Shift+N`/`Shift+P`), captions (`'c'`), playback speed (`>`/`<`), and restart (`'0'`).
  - **Fast-path Intent Parsing**: Added `parse_youtube_intent` in `ui/server.py` for instant, zero-quota execution over WebSocket and REST, plus full Gemini function calling registration in `core/brain.py`.
  - **Testing**: Added `tests/test_youtube_tool.py` with 20 unit and WebSocket integration tests (all passed).
- Built Complete Browser Automation via `BrowserControlTool` in `tools/browser_tools.py`:
  - **Universal Tab Management**: Next tab / tab ahead (`next_tab` -> `Ctrl+Tab`), previous tab / tab behind (`prev_tab` -> `Ctrl+Shift+Tab`), switch numbered tabs (`switch_tab` -> `Ctrl+1..9`), reopen closed tabs (`reopen_tab` -> `Ctrl+Shift+T`), new tab (`Ctrl+T`), and close tab (`Ctrl+W`).
  - **Page Control & Scrolling**: Scroll down, scroll up, scroll to top (`Home`), scroll to bottom (`End`), reload (`F5`), hard reload (`Ctrl+F5`), back (`Alt+Left`), forward (`Alt+Right`).
  - **Zoom & Window**: Zoom in (`Ctrl++`), zoom out (`Ctrl+-`), reset zoom (`Ctrl+0`), fullscreen (`F11`), incognito/private window, new window, history, downloads, bookmarks, and link clicking (`click_link`).
  - **Win32 Window Focusing**: Reliable foreground restoration (`AttachThreadInput` + `SetForegroundWindow` + `ShowWindow(SW_RESTORE)`).
  - **Fast-path Intent Parsing**: Added `parse_browser_intent()` in `ui/server.py` with 14 unit tests in `tests/test_browser_automation.py` (all passed).
- Built Full YouTube Music Automation via `YouTubeMusicTool` in `tools/youtube_music_tool.py`:
  - **Direct Song Streaming**: Search songs or artists and directly stream/play them via scraped video IDs mapped to `https://music.youtube.com/watch?v={id}` or search URLs.
  - **Playback & Queue Navigation**: Next song (`j` / `Shift+N`), previous song (`k` / `Shift+P`), toggle play/pause (`space`), pause, and resume.
  - **Lyrics**: Instant opening/toggling of the YouTube Music lyrics section (`e` hotkey / lyrics tab).
  - **Tab Management**: Reload music tab (`reload` -> `Ctrl+R`), open YouTube Music home page.
  - **Audio & Controls**: Volume up/down (`=`/`-`), mute (`m`), shuffle (`s`), repeat (`r`), like (`+`), dislike (`_`), seek forward 10s (`l`), rewind 10s (`h`).
  - **Fast-path Intent Parsing**: Added `parse_youtube_music_intent()` in `ui/server.py` with 12 unit tests in `tests/test_youtube_music.py` (all passed).
- Built Whole File Manager / File Explorer Control via `FileManagerTool` in `tools/file_manager_tool.py`:
  - **Physical Drives**: Lists all system disk partitions (`list_drives`) with total, free, and used space using `psutil`, and opens drives (`C:\`, `D:\`) in Windows File Explorer (`open_drive`).
  - **Folder Exploration**: Opens any folder (`open_folder`) in File Explorer including standard user aliases (`Downloads`, `Desktop`, `Documents`, `Pictures`, `Videos`, `Music`).
  - **Look at Folders**: Inspects directory contents (`look_at_folder`), reporting subdirectories, files, sizes, timestamps, and total directory sizes in human-readable formatting.
  - **Folder Search**: Fast recursive search for folders by pattern across system drives (`search_folders`) with max depth and system directory exclusion.
  - **Folder Creation**: Safely creates new directories (`create_folder`).
  - **Fast-path Intent Parsing**: Added `parse_file_manager_intent()` in `ui/server.py` with 14 unit tests in `tests/test_file_manager.py` (all passed).
- Built Skill Learner, Adaptive Memory, and Dynamic Speaking Adaptation:
  - **Custom Skill Learning**: Added skill registration in `memory/manager.py` and `tools/skill_tool.py` (`SkillLearnerTool`). Users can teach custom multi-step routines (e.g. `"learn a new skill morning routine: open Brave, open YouTube Music, and set volume to 50"` or `"when I say code mode, open vscode and open terminal"`). JARVIS registers the procedure, matches triggers, and executes sub-actions.
  - **Personal Memory & Knowledge Retention**: Learns facts, preferences, roles, and dates (e.g. `"remember that my favorite browser is Brave"`, `"remember that I am a Python developer"`, `"remember my birthday is May 14th"`).
  - **Dynamic Speaking Adaptation**:
    - `PreferenceManager.get_adaptive_prompt_context()` injects remembered user facts, preferred titles (e.g. `"call me Boss"` immediately switches honorific from `"Sir"` to `"Boss"` across fast-path and LLM contexts), and preferred speaking cadences (`speaking_style`) into Gemini's system instructions.
    - Fast-path intent parsers `parse_skill_learner_intent()` and `parse_memory_intent()` in `ui/server.py` immediately update `current_user_state` and acknowledge learned items in speech.
  - **Testing**: Added `tests/test_skill_learner.py` with 14 comprehensive unit and response tests (all passed). Full combined suite of 88 tests passing cleanly.
- Built 100% Reliable WhatsApp Launch and Zero-Phantom Messaging Protection:
  - **Windows Search Bar Launch Mechanism**:
    - Users on Windows often have WhatsApp installed via Microsoft Store (MSIX / UWP) or standalone executable where URI schemes or background processes may fail to bring up the UI.
    - Implemented native Windows Search launch automation in `WhatsAppTool._open_via_windows_search()`:
      1. Attach calling thread to interactive input desktop via `_ensure_input_desktop()` (`user32.OpenInputDesktop` + `user32.SetThreadDesktop`).
      2. Press Windows key (`pyautogui.press("win")`) to pop up Start Search menu.
      3. Type `"WhatsApp"` (`pyautogui.write("WhatsApp", interval=0.03)`).
      4. Press Enter (`pyautogui.press("enter")`) and wait for the application to initialize.
  - **Window State Verification & Foregrounding**:
    - Real-time window enumeration via Win32 `EnumWindows` and `psutil` checks on the interactive input desktop (`_find_whatsapp_window()`). Filters out IDEs, terminals, and editor titles to eliminate false positives.
    - Actively polls and verifies that a WhatsApp window exists, is visible or restored from iconic state (`SW_RESTORE`), and brought to the foreground using Win32 `AttachThreadInput` + `SetForegroundWindow` + `BringWindowToTop`.
  - **Zero-Phantom Rule (Honest Reporting)**:
    - Fixed the core issue where JARVIS previously claimed "Message sent to X on WhatsApp" even if WhatsApp was never opened or focused.
    - In `tools/whatsapp_tool.py`: `open_whatsapp()`, `search_contact()`, and `send_message()` verify that WhatsApp is genuinely open before executing keystrokes; if WhatsApp cannot be opened or focused, they immediately return `ToolResult(success=False, message="WhatsApp is not open or could not be focused...")` without typing into the void.
    - In `ui/server.py`: `parse_whatsapp_intent()` now parses `"open whatsapp"`, `"launch whatsapp"`, etc., into `action="open"`. In both `_generate_response()` and `websocket_jarvis()`, JARVIS inspects `res.success` and speaks the honest status/failure message rather than hallucinating delivery.
  - **Testing**: Updated and expanded `tools/test_whatsapp_tool.py` to 16 unit tests covering Windows Search launch, verified focus success, zero-phantom failure protection, and intent parsing. Full suite of 104 tests passing cleanly across the project.
- Built Autonomous Dev Agent, VS Code Automation, Antigravity Desktop Control, and YouTube Music Fixes:
  - **YouTube Music Playback & Search Fix**:
    - Resolved dictionary key incompatibility: `YouTubeControlTool.scrape_youtube_videos()` now populates both `"id"` and `"video_id"` keys.
    - In `YouTubeMusicTool._action_play`: Fixed video ID retrieval (`results[0].get("id") or results[0].get("video_id")`), opening `https://music.youtube.com/watch?v={id}` directly and foregrounding the window so tracks immediately play instead of opening a non-playing search result list.
    - Handled generic queries like "play songs on youtube music" by defaulting query to top hit songs.
    - In `YouTubeMusicTool._action_search`: In-app hotkey search (`'/'`) for active YouTube Music sessions with automated typing and Enter execution, with fallback to URL search.
    - In `ui/server.py`: Enhanced regexes in `parse_youtube_music_intent` to recognize all variations of "search [query] on/in youtube music", "play [query] on/in youtube music", "play songs", "search for songs", etc.
  - **Autonomous Dev Agent & VS Code Automation (`DevAgentTool` in `tools/dev_tools.py`)**:
    - `open_vscode`: Locates VS Code executable across standard system paths (`code.cmd`, `Code.exe`), automatically creates destination folder/files if they do not exist, launches VS Code, and foregrounds the window.
    - `create_file`: Generates and writes code files (`index.html`, `style.css`, `app.js`, `main.py`, etc.) with accurate modern syntaxes (semantic HTML5, responsive CSS variables/flex/grid, ES6+ event listeners, Python type-hinted templates) and verifies syntax.
    - `scaffold_project`: Scaffolds full responsive web or Python projects from scratch in any specified folder and automatically opens the project in VS Code.
    - `run_project`: Automatically starts local preview servers (`http://localhost:8000`) for web directories or executes Python scripts, reporting the exact local address and run status.
    - `check_syntax`: Validates Python, JavaScript, HTML, CSS, and JSON syntax.
    - `diagnose_error`: Analyzes tracebacks, diagnoses missing dependencies or syntax errors, and suggests/applies fixes.
  - **Google Antigravity Desktop Automation (`AntigravityControlTool` in `tools/antigravity_tools.py`)**:
    - Integrates with `C:\Users\Perfect\Desktop\Antigravity.lnk` and executable paths.
    - `launch` / `focus`: Launches or foregrounds Google Antigravity.
    - `open_folder`: Opens any workspace directory in Antigravity.
    - `new_chat`: Opens new conversations/chats in Antigravity via `Ctrl+L` / `Ctrl+Shift+L`.
    - `send_prompt`: Formulates directives with model selection (e.g., `Gemini 3.8 Flash (High)`), effort levels, priority, and file/media attachments (`@file`), pastes directly into chat, and sends via `Enter`.
    - `choose_model`: Direct model selection commands.
  - **Fast-path Intent Parsing & Tool Wiring**:
    - Wired `parse_dev_agent_intent()` and `parse_antigravity_intent()` into `ui/server.py` for both REST and WebSocket endpoints.
    - Added tools to `tools/registry.py` and `tools/__init__.py`.
    - Updated Gemini LLM function-calling group schemas in `core/brain.py`.
    - Added unit test suites `tests/test_dev_agent.py` and `tests/test_antigravity_tools.py` (44 tests passing). All 108 tests passing across the project.

## Important remaining work

1. Review whether all dormant `voice/providers/` OpenAI-compatible adapters should remain available. The active core LLM is Gemini-only; these adapters are part of a separate modular pipeline.
- The HUD voice button now runs the same Gemini Live `Charon` voice as Mark-LVI. Typed chat autoplay still uses the configured local/Edge neural TTS (`en-IN-PrabhatNeural` by default) so it does not spend another Gemini request. If the user expects every typed reply to use Charon too, that needs a separate design choice because Charon is part of the Live session.
- Check Mark-LVI's full voice interaction behavior against Project A's Live engine, especially function-call handling, reconnect/resumption, microphone/speaker errors, and user-facing failures.
- No live Gemini request or device-level audio playback was tested; verify Live connection, greeting audio, and a few Indian-English commands manually with the user's own key and devices when quota is available.
- Restart JARVIS to load backend Python changes, reload the desktop app, then verify a real Gemini response, a Downloads open, PDF output, and the user's multi-search prompt. Do not paste or log the user's key.
- Project A's WhatsApp tool now utilizes native Windows Search launch (`Win` -> `'WhatsApp'` -> `Enter`) and desktop window verification, ensuring WhatsApp is genuinely open before typing or dispatching messages and eliminating phantom claims.

## Notes on quota diagnosis

Google's Gemini quota is applied per project and varies by model and tier. The local changes remove redundant calls and shorten retained history; they cannot increase Google-side free-tier limits. Check AI Studio's project/model limits if the app still receives 429s after these fixes.
