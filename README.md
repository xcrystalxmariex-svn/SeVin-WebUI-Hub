# SeVIn AI Hub

## Repository Structure

| Branch | Contents |
|--------|----------|
| `main` | **Version 2** — `sevin-hub.tar.gz` (latest release) |
| `v1` | Version 1 — original loose source files |

---

## Version 2 (Current)

The latest Hub build is packaged as `sevin-hub.tar.gz` on the `main` branch.

### Quick Start (Termux)

```bash
# 1. Extract the archive
tar -xzf sevin-hub.tar.gz
cd sevin-hub

# 2. Install system dependencies
pkg update && pkg install python tmux

# 3. Run the wizard — installs Python packages, sets up your agents, and launches
bash wizard.sh
```

The hub opens in your browser at `http://localhost:8080`.

---

## Version 1 (Archived)

All original V1 source files are preserved on the `v1` branch:

```bash
git checkout v1
```

Files: `hub_server.py`, `agent_factory.py`, `agent_template.py`, `launch_system.py`,
`setup_wizard.py`, `terminal_wrapper.py`, `voice_processor.py`, `web_fetch.py`,
`theme.css`, `index.html`, `requirements.txt`, `wizard.sh`

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

---

## API Keys

- **Environment variable:** `export OPENAI_API_KEY=sk-...`
- **Per-agent:** Enter the key in the Create Agent dialog or wizard
- **Global:** Enter it during `setup_wizard.py`
