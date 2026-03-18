# SeVIn AI Hub

A fully local multi-agent AI system that runs in Termux on Android (or any Linux terminal).

## Quick Start (Termux)

```bash
# 1. Install system dependencies
pkg update && pkg install python tmux

# 2. Clone or download this folder, then enter it
cd sevin-hub

# 3. Run the wizard — installs Python packages, sets up your agents, and launches
bash wizard.sh
```

That's it. The hub opens in your browser at `http://localhost:8080`.

---

## Manual Setup

```bash
# Install Python packages
pip install -r requirements.txt

# Run the interactive setup wizard
python3 setup_wizard.py

# Generate agent files from agents.json
python3 agent_factory.py agents.json generated_agents/

# Start everything in tmux
python3 launch_system.py --start

# Open in browser
# http://localhost:8080  (or Cloudflare tunnel URL)
```

---

## File Overview

| File | What it does |
|------|-------------|
| `wizard.sh` | One-shot install + launch script for Termux |
| `setup_wizard.py` | Interactive CLI to create agents and set your PIN |
| `agent_factory.py` | Generates individual Flask agent servers from a template |
| `hub_server.py` | Main Flask hub — serves the web UI and all `/api/*` routes |
| `launch_system.py` | Tmux session manager (`--start`, `--stop`, `--status`, `--add-agent`) |
| `requirements.txt` | Python dependencies |
| `agents.json` | Your saved agent configurations (auto-created by wizard) |
| `config.json` | Hub port and terminal PIN hash (auto-created by wizard) |
| `static/index.html` | Web UI (single-page app, no Node.js needed) |
| `static/js/hub.js` | Frontend logic |
| `static/css/theme.css` | Cyberpunk dark theme |
| `generated_agents/` | Auto-generated per-agent Flask server files |
| `../shared_tools/` | Python tools used by agents |

---

## Creating Agents

**Via web UI:** Click **＋ New Agent**, fill in the form.

**Via CLI:**
```bash
python3 launch_system.py --add-agent "Nova" --emoji "🌟" --color "#a855f7" \
  --personality "I am Nova, a creative writing assistant." \
  --capabilities web_access voice group_chat \
  --model gpt-4o-mini
```

**Via setup wizard:**
```bash
python3 setup_wizard.py
```

---

## Agent Capabilities

| Capability | What it enables |
|------------|----------------|
| `web_access` | Agent can fetch web pages |
| `terminal` | Terminal panel shown in UI (requires PIN) |
| `voice` | Mic button + wake word + TTS audio |
| `image_gen` | DALL-E image generation |
| `file_edit` | File editing tools |
| `group_chat` | Agent can participate in group rooms |

---

## Terminal PIN

Default PIN is `1234`. Change it via the setup wizard.

The PIN is stored as a **SHA256 hash** in `config.json` — never plaintext.
Set `TERMINAL_PIN_HASH` env var to override.

**Blocked commands (safety):** `rm -rf /`, `mkfs`, `dd if=/dev/zero`, fork bombs, etc.

---

## API Keys

Set your OpenAI key in one of these ways:
- **Environment variable:** `export OPENAI_API_KEY=sk-...`
- **Per-agent:** Enter the key in the Create Agent dialog or wizard
- **Global:** Enter it during `setup_wizard.py`

---

## Launch Manager

```bash
python3 launch_system.py --start          # Start hub + all agents in tmux
python3 launch_system.py --stop           # Stop everything
python3 launch_system.py --status         # Show tmux session status
python3 launch_system.py --add-agent "X"  # Add a new agent live
```

Attach to the session: `tmux attach -t sevin-hub`

---

## Cloudflare Tunnel (access from anywhere)

All services bind to `0.0.0.0` so Cloudflare Tunnel works out of the box:

```bash
# Install cloudflared in Termux
pkg install cloudflared

# Expose hub
cloudflared tunnel --url http://localhost:8080
```

---

## Group Chat Rooms

1. Click **＋ New** next to "Group Rooms" in the sidebar
2. Name your room, select which agents to include
3. Send a message — every agent in the room responds
4. Agents can `@mention` each other

---

## Voice

- Click the mic button (🎤) to start listening
- Say **"Hey [AgentName]"** as a wake word to direct a message
- The agent's reply is spoken aloud via TTS
- STT uses the browser's Web Speech API (Chrome/Chromium works best)

---

## Shared Tools (`../shared_tools/`)

| Tool | Description |
|------|------------|
| `web_fetch.py` | Rate-limited page fetcher (10 req/min per domain) |
| `terminal_wrapper.py` | Secure command runner with PIN + blacklist |
| `voice_processor.py` | gTTS / edge-tts wrapper + wake-word detection |
