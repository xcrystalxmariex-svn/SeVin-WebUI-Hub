#!/usr/bin/env python3
"""
SeVIn AI Hub — Agent Factory
Generates individual agent server files from a template.
"""

import os
import json
from string import Template

AGENT_TEMPLATE = Template('''#!/usr/bin/env python3
"""
${agent_name} — SeVIn AI Agent
Emoji: ${emoji}
Color: ${color}
Port: ${port}
Capabilities: ${capabilities}
"""

import os
import sys
import json
import hashlib
import subprocess
import time
from urllib.parse import quote

parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(parent_dir, "shared_tools"))

try:
    from web_fetch import fetch_page
    WEB_AVAILABLE = True
except ImportError:
    WEB_AVAILABLE = False

try:
    from terminal_wrapper import execute_command, verify_pin
    TERMINAL_AVAILABLE = True
except ImportError:
    TERMINAL_AVAILABLE = False

try:
    from voice_processor import get_tts_url, detect_wake_word
    VOICE_AVAILABLE = True
except ImportError:
    VOICE_AVAILABLE = False

from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app, origins="*")

AGENT_CONFIG = {
    "id": "${agent_id}",
    "name": "${agent_name}",
    "emoji": "${emoji}",
    "color": "${color}",
    "personality": """${personality}""",
    "capabilities": ${capabilities_list},
    "port": ${port},
    "status": "online",
    "model": "${model}",
}

API_KEY = os.environ.get("OPENAI_API_KEY", "${api_key}")
WAKE_WORD = f"hey {AGENT_CONFIG['name'].lower()}"


def call_openai(messages: list, system_prompt: str) -> str:
    import urllib.request
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}",
    }
    body = json.dumps({
        "model": AGENT_CONFIG["model"],
        "messages": [{"role": "system", "content": system_prompt}] + messages,
        "max_tokens": 1024,
    }).encode()

    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=body,
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read())
        return data["choices"][0]["message"]["content"]


@app.route("/health")
def health():
    return jsonify({"status": "ok", "agent": AGENT_CONFIG["name"]})


@app.route("/info")
def info():
    return jsonify(AGENT_CONFIG)


@app.route("/chat", methods=["POST"])
def chat():
    data = request.json or {}
    message = data.get("message", "")
    history = data.get("history", [])

    system_prompt = f"""You are {AGENT_CONFIG["emoji"]} {AGENT_CONFIG["name"]}.
{AGENT_CONFIG["personality"]}
Your capabilities: {", ".join(AGENT_CONFIG["capabilities"])}.
Be helpful, concise, and respond in character."""

    messages = [{"role": m["role"], "content": m["content"]} for m in history]
    messages.append({"role": "user", "content": message})

    try:
        response = call_openai(messages, system_prompt)
        return jsonify({
            "message": response,
            "agentId": AGENT_CONFIG["id"],
            "agentName": AGENT_CONFIG["name"],
            "agentEmoji": AGENT_CONFIG["emoji"],
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/fetch", methods=["POST"])
def fetch():
    if "web_access" not in AGENT_CONFIG["capabilities"]:
        return jsonify({"error": "Web access not enabled for this agent"}), 403
    if not WEB_AVAILABLE:
        return jsonify({"error": "web_fetch tool not available"}), 503

    data = request.json or {}
    url = data.get("url", "")
    if not url:
        return jsonify({"error": "URL required"}), 400

    result = fetch_page(url)
    return jsonify(result)


@app.route("/exec", methods=["POST"])
def exec_command():
    if "terminal" not in AGENT_CONFIG["capabilities"]:
        return jsonify({"error": "Terminal access not enabled for this agent"}), 403
    if not TERMINAL_AVAILABLE:
        return jsonify({"error": "terminal_wrapper tool not available"}), 503

    data = request.json or {}
    command = data.get("command", "")
    pin = data.get("pin", "")

    if not command or not pin:
        return jsonify({"error": "command and pin are required"}), 400

    result = execute_command(command, pin)
    return jsonify(result)


@app.route("/tts", methods=["POST"])
def tts():
    if "voice" not in AGENT_CONFIG["capabilities"]:
        return jsonify({"error": "Voice not enabled for this agent"}), 403

    data = request.json or {}
    text = data.get("text", "")
    lang = data.get("lang", "en")

    if not text:
        return jsonify({"error": "text required"}), 400

    audio_url = get_tts_url(text, lang) if VOICE_AVAILABLE else f"https://translate.google.com/translate_tts?ie=UTF-8&tl={lang}&client=tw-ob&q={quote(text[:200])}"
    return jsonify({"audioUrl": audio_url, "text": text})


@app.route("/stt", methods=["POST"])
def stt():
    if "voice" not in AGENT_CONFIG["capabilities"]:
        return jsonify({"error": "Voice not enabled for this agent"}), 403

    data = request.json or {}
    transcript = data.get("transcript", "")

    wake_triggered = VOICE_AVAILABLE and detect_wake_word(transcript, AGENT_CONFIG["name"])

    return jsonify({
        "wakeWord": WAKE_WORD,
        "triggered": wake_triggered,
        "transcript": transcript,
    })


@app.route("/generate_image", methods=["POST"])
def generate_image():
    if "image_gen" not in AGENT_CONFIG["capabilities"]:
        return jsonify({"error": "Image generation not enabled for this agent"}), 403

    data = request.json or {}
    prompt = data.get("prompt", "")
    if not prompt:
        return jsonify({"error": "prompt required"}), 400

    try:
        import urllib.request
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_KEY}",
        }
        body = json.dumps({
            "model": "dall-e-3",
            "prompt": prompt,
            "n": 1,
            "size": "1024x1024",
        }).encode()
        req = urllib.request.Request(
            "https://api.openai.com/v1/images/generations",
            data=body,
            headers=headers,
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            result = json.loads(resp.read())
            image_url = result["data"][0]["url"]
            return jsonify({"imageUrl": image_url, "prompt": prompt})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    print(f"Starting {AGENT_CONFIG["emoji"]} {AGENT_CONFIG["name"]} on port {AGENT_CONFIG["port"]}...")
    app.run(host="0.0.0.0", port=AGENT_CONFIG["port"], debug=False)
''')


class AgentFactory:
    def __init__(self, output_dir: str = "."):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def create_agent(self, config: dict) -> str:
        import uuid
        agent_id = config.get("id", str(uuid.uuid4()))
        agent_name = config["name"]
        safe_name = agent_name.replace(" ", "_").replace("-", "_").lower()
        filename = f"{safe_name}_main.py"
        filepath = os.path.join(self.output_dir, filename)

        capabilities_list = json.dumps(config.get("capabilities", []))

        content = AGENT_TEMPLATE.substitute(
            agent_id=agent_id,
            agent_name=agent_name,
            emoji=config.get("emoji", "🤖"),
            color=config.get("color", "#6366f1"),
            personality=config.get("personality", f"I am {agent_name}, a helpful AI assistant."),
            capabilities=", ".join(config.get("capabilities", [])),
            capabilities_list=capabilities_list,
            port=config.get("port", 8001),
            model=config.get("model", "gpt-4o-mini"),
            api_key=config.get("apiKey", ""),
        )

        with open(filepath, "w") as f:
            f.write(content)

        os.chmod(filepath, 0o755)
        print(f"  ✓ Generated: {filepath}")
        return filepath

    def create_all_agents(self, agents_file: str) -> list[str]:
        with open(agents_file) as f:
            agents = json.load(f)

        generated = []
        for agent in agents:
            path = self.create_agent(agent)
            generated.append(path)

        return generated


if __name__ == "__main__":
    import sys
    agents_file = sys.argv[1] if len(sys.argv) > 1 else "agents.json"
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "generated_agents"

    factory = AgentFactory(output_dir)
    files = factory.create_all_agents(agents_file)
    print(f"\nGenerated {len(files)} agent file(s) in {output_dir}/")
