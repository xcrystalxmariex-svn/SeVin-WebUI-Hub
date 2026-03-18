#!/usr/bin/env python3
"""
SeVIn AI Hub — Agent Factory
Generates individual agent Flask server files from a template.
"""

import os
import json
import uuid
from string import Template

AGENT_TEMPLATE = Template(r'''#!/usr/bin/env python3
"""
${agent_name} Agent Server
Emoji: ${emoji}  |  Color: ${color}  |  Port: ${port}
Capabilities: ${capabilities}
"""

import os, sys, json, hashlib, subprocess, time
from urllib.parse import quote

_base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_base, "shared_tools"))

try:
    from web_fetch import fetch_page as _fetch
except ImportError:
    _fetch = None

try:
    from terminal_wrapper import execute_command as _exec
except ImportError:
    _exec = None

try:
    from voice_processor import get_tts_url as _tts_url
except ImportError:
    _tts_url = None

from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app, origins="*")

CONFIG = {
    "id":           "${agent_id}",
    "name":         "${agent_name}",
    "emoji":        "${emoji}",
    "color":        "${color}",
    "personality":  """${personality}""",
    "capabilities": ${capabilities_list},
    "port":         ${port},
    "status":       "online",
    "model":        "${model}",
}

API_KEY  = os.environ.get("OPENAI_API_KEY", "${api_key}")
WAKE_WD  = f"hey {CONFIG['name'].lower()}"


def _openai(messages, system):
    import urllib.request
    body = json.dumps({
        "model": CONFIG["model"],
        "messages": [{"role": "system", "content": system}] + messages,
        "max_tokens": 1024,
    }).encode()
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=body,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())["choices"][0]["message"]["content"]


@app.route("/health")
def health():
    return jsonify({"status": "ok", "agent": CONFIG["name"]})


@app.route("/info")
def info():
    return jsonify(CONFIG)


@app.route("/chat", methods=["POST"])
def chat():
    data = request.json or {}
    hist = [{"role": m["role"], "content": m["content"]} for m in data.get("history", [])]
    hist.append({"role": "user", "content": data.get("message", "")})
    system = (f"You are {CONFIG['emoji']} {CONFIG['name']}. {CONFIG['personality']}\n"
              f"Capabilities: {', '.join(CONFIG['capabilities'])}. Be helpful and concise.")
    try:
        reply = _openai(hist, system)
        return jsonify({"message": reply, "agentId": CONFIG["id"],
                        "agentName": CONFIG["name"], "agentEmoji": CONFIG["emoji"]})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/fetch", methods=["POST"])
def fetch():
    if "web_access" not in CONFIG["capabilities"]:
        return jsonify({"error": "web_access not enabled"}), 403
    if not _fetch:
        return jsonify({"error": "web_fetch tool unavailable"}), 503
    url = (request.json or {}).get("url", "")
    return jsonify(_fetch(url)) if url else (jsonify({"error": "url required"}), 400)


@app.route("/exec", methods=["POST"])
def exec_cmd():
    if "terminal" not in CONFIG["capabilities"]:
        return jsonify({"error": "terminal not enabled"}), 403
    if not _exec:
        return jsonify({"error": "terminal_wrapper unavailable"}), 503
    d = request.json or {}
    if not d.get("command") or not d.get("pin"):
        return jsonify({"error": "command and pin required"}), 400
    return jsonify(_exec(d["command"], d["pin"]))


@app.route("/tts", methods=["POST"])
def tts():
    if "voice" not in CONFIG["capabilities"]:
        return jsonify({"error": "voice not enabled"}), 403
    d = request.json or {}
    text, lang = d.get("text", ""), d.get("lang", "en")
    url = (_tts_url(text, lang) if _tts_url
           else f"https://translate.google.com/translate_tts?ie=UTF-8&tl={lang}&client=tw-ob&q={quote(text[:200])}")
    return jsonify({"audioUrl": url, "text": text})


@app.route("/stt", methods=["POST"])
def stt():
    if "voice" not in CONFIG["capabilities"]:
        return jsonify({"error": "voice not enabled"}), 403
    transcript = (request.json or {}).get("transcript", "")
    return jsonify({"wakeWord": WAKE_WD,
                    "triggered": WAKE_WD in transcript.lower(),
                    "transcript": transcript})


@app.route("/generate_image", methods=["POST"])
def gen_image():
    if "image_gen" not in CONFIG["capabilities"]:
        return jsonify({"error": "image_gen not enabled"}), 403
    prompt = (request.json or {}).get("prompt", "")
    if not prompt:
        return jsonify({"error": "prompt required"}), 400
    try:
        import urllib.request
        body = json.dumps({"model": "dall-e-3", "prompt": prompt, "n": 1, "size": "1024x1024"}).encode()
        req = urllib.request.Request(
            "https://api.openai.com/v1/images/generations",
            data=body,
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=60) as r:
            img_url = json.loads(r.read())["data"][0]["url"]
        return jsonify({"imageUrl": img_url, "prompt": prompt})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    print(f"▶  {CONFIG['emoji']} {CONFIG['name']}  →  port {CONFIG['port']}")
    app.run(host="0.0.0.0", port=CONFIG["port"], debug=False)
''')


class AgentFactory:
    def __init__(self, output_dir: str = "generated_agents"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def create_agent(self, config: dict) -> str:
        agent_id   = config.get("id") or str(uuid.uuid4())
        agent_name = config["name"]
        safe       = agent_name.replace(" ", "_").replace("-", "_").lower()
        filename   = f"{safe}_main.py"
        filepath   = os.path.join(self.output_dir, filename)

        content = AGENT_TEMPLATE.substitute(
            agent_id         = agent_id,
            agent_name       = agent_name,
            emoji            = config.get("emoji", "🤖"),
            color            = config.get("color", "#6366f1"),
            personality      = config.get("personality", f"I am {agent_name}, a helpful AI assistant."),
            capabilities     = ", ".join(config.get("capabilities", [])),
            capabilities_list= json.dumps(config.get("capabilities", [])),
            port             = config.get("port", 8001),
            model            = config.get("model", "gpt-4o-mini"),
            api_key          = config.get("apiKey", ""),
        )

        with open(filepath, "w") as f:
            f.write(content)
        os.chmod(filepath, 0o755)
        return filepath

    def create_all_agents(self, agents_file: str) -> list[str]:
        with open(agents_file) as f:
            agents = json.load(f)
        return [self.create_agent(a) for a in agents]


if __name__ == "__main__":
    import sys
    agents_file = sys.argv[1] if len(sys.argv) > 1 else "agents.json"
    output_dir  = sys.argv[2] if len(sys.argv) > 2 else "generated_agents"
    files = AgentFactory(output_dir).create_all_agents(agents_file)
    print(f"\nGenerated {len(files)} agent file(s) in {output_dir}/")
    for f in files:
        print(f"  {f}")
