# JARVIS Messaging Module

**Responsible Engineer:** Trupti  
**Role:** Messaging (Telegram Bot, Remote Assistant Reach, WhatsApp, Reminders, Autonomous Tools)  
**Branch:** `feature/trupti-messaging`  
**Milestone:** Days 1 to 8 Deliverables Complete (46 Tests Passing)

---

## 1. Overview

The `messaging` module powers remote access to JARVIS through Telegram and WhatsApp. It enables the user to communicate with JARVIS from their mobile phone, receive answers from `JarvisBrain`, trigger autonomous tools from CLI or Brain, capture laptop screenshots remotely, exchange photos and documents securely, send verified WhatsApp messages, schedule persistent reminders, and execute messaging directives via autonomous function calling.

### Deliverables Covered (Days 1 – 8)

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

* **Day 6: WhatsApp Messaging + Verified Contacts**
  * `messaging/contacts.py`:
    * `load_contacts() -> dict`: Loads `contacts.json` if available, falls back to `contacts.example.json`.
    * `find_contact(name: str) -> str | None`: Case-insensitive, whitespace-agnostic contact phone lookup.
  * `messaging/whatsapp.py`:
    * `send_whatsapp(contact: str, message: str) -> str`: Automates WhatsApp Web delivery via `pywhatkit`.
    * **Safety Guard:** Strict contact validation. Refuses unknown recipients politely; never sends to unverified numbers. Never raises.
  * `messaging/test_whatsapp.py`: Provides `--dry-run` mode to preview outbound messages without opening browsers.

* **Day 7: Persistent Telegram Reminders**
  * `messaging/reminders.py`:
    * `set_reminder(when: str, text: str) -> str`: Parses natural timings ('HH:MM' 24h format or 'in N minutes').
    * Persists reminders in `messaging/reminders.json` to survive application restarts.
    * Resilient background monitoring thread checking every 20 seconds and dispatching due alerts via `send_telegram()`.
  * `messaging/test_reminders.py`: Interactive and `--verify` runner for scheduling and verifying reminders.

* **Day 8: Full Autonomous Messaging Tools Suite (WhatsApp, Reminders, Telegram)**
  * `messaging/tools.py`:
    * `SendWhatsAppTool`: Autonomous WhatsApp dispatch with contacts lookup validation and error handling.
    * `SetReminderTool`: Autonomous reminder scheduling callable by AI Brain or CLI (`execute_tool("set_reminder", {"when": "in 10 minutes", "text": "Call doctor"})`).
    * `ListRemindersTool`: Autonomous listing of pending active alerts.
    * Canonical export: `TOOLS = [SendTelegramTool(), SendWhatsAppTool(), SetReminderTool(), ListRemindersTool()]` auto-registered into `TOOL_REGISTRY`.
  * Unit test suite expanded to **46 comprehensive tests** in `tests/test_messaging.py` with 100% pass rate.
  * 1-click verification runner: `messaging/verify_day8.bat`.

---

## 2. Setup Guide

### Step 1: Telegram Bot Token
1. Create a bot with `@BotFather` on Telegram.
2. Put your token in `.env`:
   ```env
   TELEGRAM_BOT_TOKEN=your_bot_token_here
   TELEGRAM_OWNER_ID=
   ```

### Step 2: Saved Contacts for WhatsApp
1. Copy `messaging/contacts.example.json` to `messaging/contacts.json`:
   ```json
   {
     "Jayesh": "+919876543210",
     "MyPhone": "+919123456789"
   }
   ```
2. Real phone numbers in `contacts.json` are automatically ignored by Git.

---

## 3. Running & Testing

### Running All 46 Unit Tests
```powershell
python -m pytest tests/test_messaging.py -v
```

### Running 1-Click Verification Batch
```powershell
messaging\verify_day8.bat
```

### Quick Day 8 Acceptance Test
```powershell
messaging\run_day8_test.bat
```

---

## 4. Git Commands for Day 8

```powershell
# Verify status (only messaging/ and tests/ touched, .env excluded)
git status

# Stage changes
git add messaging/tools.py messaging/__init__.py messaging/README.md tests/test_messaging.py

# Commit
git commit -m "feat(messaging): complete Day 8 autonomous messaging tools (WhatsApp, Reminders) and central registry auto-loader"

# Push to your branch
git push origin feature/trupti-messaging
```
