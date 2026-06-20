# Local Voice Assistant

A private, offline-first personal assistant (like Alexa/Siri) that runs on your
Windows PC. It listens for a wake word, understands commands with a **local LLM**
(via Ollama), and controls your computer and connected devices. Nothing leaves
your machine except optional phone push notifications.

## What it can do

45 built-in skills, including:

- **Accessibility / hands-free control** (the "eyes" and "hands"):
  - *Read the screen aloud*, describe the active window, say which field has focus
    and its contents.
  - *Click any button/link/menu by name* ("click Submit") via Windows UI Automation,
    with OCR click as a fallback.
  - *Focus and type into fields by name*; list what's clickable; scroll.
  - *Dictation mode* — speak and it types into the focused field, with spoken
    editing commands ("new line", "delete that", "stop dictation").
  - *Hands-free conversation* — keep talking without repeating the wake word; or
    turn on always-listening mode for fully no-touch use.
- **Apps & system** — open/close apps, set/adjust volume, media play/pause/next,
  screenshots, system status (CPU/RAM/disk/battery), screen brightness,
  lock/sleep/shutdown/restart.
- **Windows & input** — show desktop, switch/maximize/minimize/close window,
  list open windows, press arbitrary hotkeys, type text, clipboard read/copy.
- **Web & files** — open websites, web search, play on YouTube, open folders,
  search for files.
- **Productivity** — timers, reminders (relative or at a clock time), notes,
  weather, the date/time.
- **Phone notifications** — push reminders/messages to your phone via [ntfy](https://ntfy.sh).
- **Other computers** — run commands on other machines over SSH.
- **Voice** — custom wake word (default **"ekko"**), offline speech-to-text
  (Whisper), offline text-to-speech.

## Accessibility / fully hands-free use

This system is built so someone can drive the computer with voice alone:

1. Set `assistant.hands_free: true` in `config.yaml` for always-listening (no wake
   word), or keep `conversation_follow_up: true` to chain commands after one wake.
2. Ask it to be your eyes: *"what's on my screen"*, *"read this to me"*,
   *"what field am I in"*.
3. Operate apps by voice: *"open Chrome"*, *"click the address bar"*,
   *"type my email address"*, *"click Sign in"*, *"scroll down"*.
4. Compose text: *"take dictation"* → speak → *"new line"* → … → *"stop dictation"*.

It uses the same accessibility API as screen readers (UI Automation), so it works
best in apps that expose accessibility info (most native and well-built apps), and
falls back to OCR for the rest.

## Wake word

Default wake word is **"ekko"** (accepts aliases: "echo", "ecko", "eko"). Set any wake word in `config.yaml` → `assistant.wake_word`. Two backends:

- **Pretrained (low CPU):** `hey_jarvis`, `alexa`, `hey_mycroft`, `hey_rhasspy`
  use openWakeWord.
- **Any custom word** (like `ekko`): handled by a lightweight Whisper spotter —
  it transcribes short speech bursts and matches your word. No training needed.
  Configure aliases in `assistant.wake_word_aliases` for common variations.

**Two-step rhythm:** Say the wake word (e.g. "Ekko") → wait for the reply "Yes?" →
then speak your command. This two-step approach is reliable; one-breath commands
("Ekko, open notepad") are supported but less reliable in noisy environments.

## Architecture

```
mic ─▶ wake word ─▶ record ─▶ speech-to-text ─▶ ┌─────────┐ ─▶ tools ─▶ PC / phone / SSH
(openWakeWord)      (VAD)     (faster-whisper)   │  Brain  │
                                       speak ◀── │ (Ollama)│ ◀── tool results
                                    (pyttsx3)     └─────────┘
```

- `assistant/brain/` — Ollama client + tool-calling loop + tool registry.
- `assistant/skills/` — the actual capabilities (pc_control, notifications, remote).
- `assistant/audio/` — wake word, recorder, speech-to-text, text-to-speech.
- `assistant/main.py` — orchestration + CLI.

## Setup

### 1. Install Ollama and a model
Download Ollama from https://ollama.com, then pull a tool-capable model:
```powershell
ollama pull qwen2.5:3b
```
(`qwen2.5:3b` is light enough for a GTX 1050. For more accuracy try `llama3.1:8b`.)

### 2. Install Python dependencies
```powershell
py -m pip install -r requirements-core.txt    # text mode + all skills
py -m pip install -r requirements-voice.txt   # add voice (wake word, STT, TTS)
```

### 3. Configure
```powershell
copy config.example.yaml config.yaml
```
Edit `config.yaml` — at minimum set `notifications.ntfy_topic` (a long secret
string) if you want phone push, and add any `remote_hosts`.

## Run standalone (no VS Code / no terminal)

Just **double-click the "Ekko Assistant" shortcut on your Desktop** (or
`start_assistant.bat` in this folder). A window opens, it warms up (~1-2 min the
first time on a cold start), then says **"Ekko is ready"** out loud, and starts
listening.

**Usage:**
1. Say the wake word: **"Ekko"** (or an alias like "Echo")
2. Listen for the reply: **"Yes?"** (confirming it heard you)
3. Say your command: **"open notepad"**, **"what's my battery"**, **"set volume to 30"**, etc.
4. It replies **out loud** through your speakers

- To stop it: close the window (or press Ctrl+C)
- `start_assistant_hidden.vbs` runs it with no visible window (stop it via Task Manager)
- Subsequent starts are faster (~10-30s) if the model stays warm

## British (UK English) voice

Ekko speaks with whatever voice Windows has. To get a British accent, run the
included installer once:

**Double-click `install_uk_voice.bat`** → approve the admin prompt. It will:
1. Download the British voice (Hazel/George/Susan) via Windows Capabilities
2. Expose it to Ekko (Windows 11 hides modern voices from classic apps by default;
   the script copies the en-GB voice token from the OneCore store into the SAPI5
   store to fix that)
3. Show a completion summary with available British voices

After installation, **close and reopen Settings and any voice-using apps** (including
Ekko) so Windows reloads the voice list. `config.yaml` has `tts.voice: "en-gb"`,
so Ekko will automatically pick the British voice on the next run.

Replies also use British spelling/phrasing.

## Auto-start at logon

A shortcut in your Startup folder (`shell:startup`) runs `ekko_autostart.vbs` hidden
at every logon, logging to `ekko.log`. To disable, delete that shortcut from the
Startup folder.

## Run from a terminal

```powershell
py -m assistant.main --check        # verify Ollama + model are reachable
py -m assistant.main --text         # type commands (no microphone needed)
py -m assistant.main                # full voice mode with wake word
py -m assistant.main --list-audio   # find your microphone's device index
py -m assistant.main --list-voices  # list available TTS voices
```

Try in text mode: `what's my battery level`, `open notepad`, `set volume to 30`,
`take a screenshot`, `search the web for pizza near me`,
`send a notification to my phone saying the build is done`.

## Phone notifications (ntfy)

1. Install the **ntfy** app (Android/iOS).
2. Subscribe to a unique, hard-to-guess topic, e.g. `my-pc-7h3kd9`.
3. Put that topic in `config.yaml` → `notifications.ntfy_topic`.

## Controlling other computers

Add machines under `remote_hosts` in `config.yaml`. Key-based SSH auth is
strongly recommended over passwords. Remote commands ask for confirmation first.

## Safety

Destructive actions (shutdown, restart, remote commands) are marked *dangerous*
and require confirmation (`require_confirmation_for_dangerous: true`). Shutdown/
restart use a 5-second delay; say "cancel shutdown" to abort.

## Troubleshooting

**Ekko doesn't hear my wake word:**
- Confirm your microphone works: `py -m assistant.main --list-audio` (pick your device's index, add to `config.yaml` → `audio.device_index`)
- Check wake word spelling in `config.yaml` → `assistant.wake_word`
- Try an alias (e.g. "echo" instead of "ekko") — custom words can be phonetically sensitive
- Test in text mode: `py -m assistant.main --text`, then type a command to verify the brain works

**Ekko doesn't reply aloud:**
- Confirm speakers work and aren't muted
- Test: `py -m assistant.main --list-voices` (should list at least one voice)
- If using UK voice, re-run `install_uk_voice.bat` and close/reopen voice-using apps

**Ollama connection fails:**
- Verify Ollama is running: `ollama list` in a terminal (if it errors, run `ollama serve`)
- Confirm the model is downloaded: `ollama pull qwen2.5:3b`
- Check Ollama is at `http://localhost:11434` (default); set `llm.ollama_base_url` in `config.yaml` if different

**"Request timed out" errors:**
- Increase `llm.timeout` in `config.yaml` (default 300s, increase for slow GPUs like GTX 1050)
- Decrease model size (`llama2` instead of `qwen2.5:3b`) or use `--text` mode to debug

## Extend it

Add a new capability by writing a function in a `skills/` module and decorating it
with `@tool(...)`. It's automatically exposed to the assistant. Smart-home
integrations (Hue, smart plugs) can be added the same way.
