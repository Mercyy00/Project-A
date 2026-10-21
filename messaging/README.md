# JARVIS Messaging Module

**Responsible Engineer:** Trupti  
**Role:** Messaging (Telegram Bot, Remote Assistant Reach, Notifications)  
**Branch:** `feature/trupti-messaging`  
**Milestone:** Day 1 to Day 3 Deliverables Complete

---

## 1. Overview

The `messaging` module powers remote access to JARVIS through Telegram. It enables the user to communicate with JARVIS from their mobile phone, receive answers from `JarvisBrain`, and send automated notifications or documents.

### Deliverables Covered (Days 1 – 3)
* **Day 1: Setup + Create the Telegram Bot**
  * Private Python environment with dependencies (`pyTelegramBotAPI`, `python-dotenv`, `pytest`, `schedule`, `pywhatkit`).
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
  * `messaging/test_bot_brain.py`: Instantiates `JarvisBrain` from `core.brain` (with pre-merge standalone fallback) and wires incoming messages to `brain.chat`.

---

## 2. Setup Guide

### Step 1: Create your Telegram Bot with BotFather
1. Open the Telegram app and search for `@BotFather`.
2. Send the command: `/newbot`.
3. Provide a friendly name for your bot (e.g., `MyJarvisAssistant`).
4. Choose a unique username ending with `bot` (e.g., `jarvis_trupti_assistant_bot`).
5. Copy the HTTP API token provided by BotFather.

### Step 2: Configure `.env`
1. Copy `.env.example` to `.env` if not already done:
   ```powershell
   cp .env.example .env
   ```
2. Open `.env` and paste your bot token:
   ```env
   TELEGRAM_BOT_TOKEN=123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ
   TELEGRAM_OWNER_ID=
   ```
3. Keep `TELEGRAM_OWNER_ID` empty for the first run.

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

### Running the Day 2 Echo Bot (Background Thread)
```powershell
python messaging/test_bot.py
```
* Messages sent by the owner are echoed back.
* Messages from unauthorized users are silently ignored.
* Press `Ctrl+C` to terminate the background thread cleanly.

### Running Day 3 Jarvis Brain Integration
```powershell
python messaging/test_bot_brain.py
```
* Connects the bot directly to `JarvisBrain.chat`.
* Ask `"What is the date today?"` from Telegram to receive the verified response.

### Automated Verifications & Acceptance Tests
Run the standalone verification suites:
```powershell
python messaging/telegram_bot.py --verify
python messaging/test_bot.py --verify
python messaging/test_bot_brain.py --verify
```

### Running Full Unit Test Suite (pytest)
```powershell
python -m pytest tests/test_messaging.py -v
```

---

## 4. Git Commands for Day 1 – Day 3

As specified in the team workflow guide:

```powershell
# Verify .env and untracked files are excluded
git status

# Add messaging files
git add requirements.txt .env.example .gitignore
git add messaging/telegram_bot.py messaging/test_bot.py messaging/test_bot_brain.py messaging/contacts.example.json
git add tests/test_messaging.py messaging/README.md

# Commit
git commit -m "feat(messaging): complete Day 1 to Day 3 Telegram bot with brain integration"

# Push to your branch
git push -u origin feature/trupti-messaging
```

---

## 5. Security & Boundary Rules

1. **Owner-Only Security**: All messages are strictly validated against `TELEGRAM_OWNER_ID`. Strangers receive no reply or acknowledgement.
2. **Never Expose Tokens**: `TELEGRAM_BOT_TOKEN` is loaded dynamically from `.env` and is never printed, logged, or checked into Git.
3. **Folder Boundary**: All code edits are restricted exclusively to `messaging/` and `tests/test_messaging.py`.
