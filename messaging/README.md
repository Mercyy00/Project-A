# JARVIS Messaging Module

**Responsible Engineer:** Trupti  
**Role:** Messaging (Telegram Bot, Remote Assistant Reach, Notifications)  
**Branch:** `feature/trupti-messaging`  
**Milestone:** Day 1 to Day 5 Deliverables Complete

---

## 1. Overview

The `messaging` module powers remote reach for JARVIS through Telegram. It enables the user to communicate with JARVIS from their mobile phone, receive answers from `JarvisBrain`, trigger autonomous tools from CLI or Brain, capture laptop screenshots remotely, and exchange photos and documents securely.

### Deliverables Covered (Days 1 – 5)

* **Day 1: Setup + Create Telegram Bot**
  * Private Python environment with dependencies (`pyTelegramBotAPI`, `python-dotenv`, `pytest`, `schedule`, `pywhatkit`, `pydantic`).
  * Secure configuration architecture via `.env.example` and local `.env` (strictly excluded from Git).
  * Safe contacts example file (`messaging/contacts.example.json`).

* **Day 2: Owner-Only Echo Bot**
  * `messaging/telegram_bot.py`: Reads token from `.env` without ever logging or exposing it.
  * Filters incoming messages by numeric `TELEGRAM_OWNER_ID`. Ignores strangers completely.
  * If `TELEGRAM_OWNER_ID` is unset, prints the chat ID to console with instructions and stays silent.
  * `messaging/test_bot.py`: Runs the bot in a background daemon thread with clean `Ctrl+C` shutdown.

* **Day 3: Connect Bot to Jarvis Brain**
  * `start_bot(handler: Callable[[str], str])`: Routes messages from the owner to `handler(text)` and sends replies back.
  * Splits long replies exceeding Telegram's 4096-character limit into clean chunks.
  * Catches exceptions in the handler and politely responds `"Sorry, something went wrong."` without crashing.
  * `send_telegram(text: str, file_path: str | None = None) -> bool`: Sends text or document attachments directly to the owner. Never raises; logs errors and returns `False` on failure.
  * `messaging/test_bot_brain.py`: Instantiates `JarvisBrain` from `core.brain` and wires incoming messages to `brain.chat`.

* **Day 4: Commands & SendTelegramTool (SYNC 1)**
  * Added bot commands: `/start` (welcome), `/help` (command directory), and `/status` (current time and `'Jarvis is online'`).
  * Created `messaging/tools.py` with `SendTelegramTool(text: str)` inheriting `BaseTool` from `tools.base`.
  * Allows Jarvis Brain and CLI to autonomously send messages to the owner (`execute_tool("send_telegram", {"text": "hello"})`).
  * Automatically registered in `tools.registry.TOOL_REGISTRY`.

* **Day 5: Files, Photos & Remote /screenshot**
  * Extended `send_telegram`:
    * Files ending in `.png`, `.jpg`, `.jpeg` sent as high-res photos via `bot.send_photo`.
    * Other files sent as documents via `bot.send_document`.
    * Strict security boundary: only allows files inside `workspace/` or `temp_*` folders.
    * Enforces 45 MB maximum file size limit with clean logging.
  * Added `/screenshot` command:
    * Uses `vision.screen.take_screenshot()` to capture the laptop screen and deliver it to the owner.
    * Respects privacy toggle: replies with friendly message when `VISION_PAUSED=1`.
    * Gracefully handles `ImportError` if vision module is not present.
  * Added owner photo handler:
    * Automatically downloads photos sent by the owner into `workspace/` and replies `"Saved"`.

---

## 2. Setup Guide

### Step 1: Create your Telegram Bot with BotFather
1. Open the Telegram app and search for `@BotFather`.
2. Send the command: `/newbot`.
3. Provide a friendly name for your bot (e.g., `MyJarvisAssistant`).
4. Choose a unique username ending with `bot` (e.g., `jarvis_trupti_assistant_bot`).
5. Copy the HTTP API token provided by BotFather.

### Step 2: Configure `.env`
1. Open `.env` and paste your bot token:
   ```env
   TELEGRAM_BOT_TOKEN=123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ
   TELEGRAM_OWNER_ID=
   ```
2. Keep `TELEGRAM_OWNER_ID` empty for the first run.

### Step 3: Discover Your Telegram Chat ID
1. Run the test bot:
   ```powershell
   python messaging/test_bot.py
   ```
2. Open your Telegram app, search for your bot's username, and send `"hi"`.
3. The terminal console will display:
   ```
   [JARVIS Bot] Incoming message from chat ID: 987654321
   Please add TELEGRAM_OWNER_ID=987654321 to your .env file and restart.
   ```
4. Copy your numeric chat ID into `.env`:
   ```env
   TELEGRAM_OWNER_ID=987654321
   ```
5. Restart the bot (`Ctrl+C` then re-run). Your bot is now active and private to you!

---

## 3. Running & Testing

### Running the Live Brain Bot (Commands + Chat + Screenshot)
```powershell
python messaging/test_bot_brain.py
```
* Supports `/start`, `/help`, `/status`, and `/screenshot`.
* Any plain text routes through `JarvisBrain.chat`.
* Any photo sent to the bot is saved in `workspace/`.

### Running Verification Tests (Day 3, 4, 5)
```powershell
# Acceptance verification
python messaging/test_bot_brain.py --verify
python messaging/tools.py
python messaging/telegram_bot.py --verify

# Full PyTest Suite (25 Tests)
python -m pytest tests/test_messaging.py -v
```

---

## 4. Git Commands for Day 4 – Day 5

```powershell
# Verify status (only messaging/ and tests/ touched, .env excluded)
git status

# Stage changes
git add messaging/telegram_bot.py messaging/tools.py messaging/__init__.py messaging/README.md tests/test_messaging.py

# Commit
git commit -m "feat(messaging): Day 4-5 bot commands, SendTelegramTool, /screenshot, and photo handling"

# Push to your branch
git push origin feature/trupti-messaging
```

---

## 5. Viva & Interview Questions Reference

**Q1: How does owner-only authorization work?**  
*Answer:* Every incoming update inspects `message.chat.id`. If it does not match `TELEGRAM_OWNER_ID` from `.env`, the update is silently ignored. If `TELEGRAM_OWNER_ID` is not yet configured, the bot prints the ID to the server console and does not reply to the sender.

**Q2: How does the bot handle network drops?**  
*Answer:* We use `bot.infinity_polling(timeout=10, long_polling_timeout=5)` which catches connection resets and timeouts automatically and continues retrying without crashing.

**Q3: How does SendTelegramTool integrate with Jarvis Brain?**  
*Answer:* `SendTelegramTool` inherits `BaseTool` from `tools.base`. It provides a JSON schema describing its `text` parameter. When the user asks Jarvis "send me a telegram message", the brain generates a tool call to `send_telegram`, which dispatches to `send_telegram(text)`.

**Q4: What security restrictions are placed on file delivery?**  
*Answer:* `send_telegram()` enforces two security checks: files must reside strictly inside `workspace/` or `temp_*` directories (preventing path traversal or system file leakage), and file sizes cannot exceed 45 MB.
