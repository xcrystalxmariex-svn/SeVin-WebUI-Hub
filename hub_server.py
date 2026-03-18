#!/usr/bin/env python3
"""
SeVIn AI Hub — Main Flask Hub Server
Manages agent registry, group chat rooms, terminal, and static file serving.
"""

import os
import sys
import json
import hashlib
import subprocess
import uuid
import time
import re
from typing import Optional
from urllib.parse import quote

BASE_DIR_EARLY = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(BASE_DIR_EARLY, "shared_tools"))
sys.path.insert(0, BASE_DIR_EARLY)

from flask import Flask, request, jsonify, send_from_directory, send_file
from flask_cors import CORS
try:
    from flask_socketio import SocketIO, emit, join_room, leave_room
    SOCKETIO_AVAILABLE = True
except ImportError:
    SOCKETIO_AVAILABLE = False

try:
    from agent_factory import AgentFactory
    FACTORY_AVAILABLE = True
except ImportError:
    FACTORY_AVAILABLE = False

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
DATA_DIR = os.path.join(BASE_DIR, "data")
AGENTS_FILE = os.path.join(BASE_DIR, "agents.json")
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
SHARED_TOOLS_DIR = os.path.join(BASE_DIR, "shared_tools")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)

app = Flask(__name__, static_folder=STATIC_DIR)
CORS(app, origins="*")

if SOCKETIO_AVAILABLE:
    socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

agents: dict[str, dict] = {}
rooms: dict[str, dict] = {}

DEFAULT_PIN_HASH = "03ac674216f3e15c761ee1a5e255f067953623c8b388b4459e13f978d7c846f4"
DANGEROUS_PATTERNS = [
    r"rm\s+-rf\s+/",
    r"mkfs",
    r"dd\s+if=/dev/zero",
    r":\(\)\{\s*:\|:&\s*\};:",
    r"chmod\s+777\s+/",
    r">\s*/dev/sda",
]

next_port = [8001]


def load_config() -> dict:
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE) as f:
            return json.load(f)
    return {}


def load_agents():
    global agents
    if os.path.exists(AGENTS_FILE):
        with open(AGENTS_FILE) as f:
            agent_list = json.load(f)
        for agent in agent_list:
            if "id" not in agent:
                agent["id"] = str(uuid.uuid4())
            agents[agent["id"]] = agent
        print(f"Loaded {len(agents)} agent(s) from {AGENTS_FILE}")


def save_agents():
    with open(AGENTS_FILE, "w") as f:
        json.dump(list(agents.values()), f, indent=2)


def hash_pin(pin: str) -> str:
    return hashlib.sha256(pin.encode()).hexdigest()


def is_dangerous(command: str) -> bool:
    return any(re.search(p, command, re.IGNORECASE) for p in DANGEROUS_PATTERNS)


def call_openai(agent: dict, messages: list) -> str:
    import urllib.request
    api_key = agent.get("apiKey") or os.environ.get("OPENAI_API_KEY", "")
    model = agent.get("model", "gpt-4o-mini")
    system = f"""You are {agent['emoji']} {agent['name']}. {agent['personality']}
Capabilities: {', '.join(agent.get('capabilities', []))}. Be helpful and concise."""

    body = json.dumps({
        "model": model,
        "messages": [{"role": "system", "content": system}] + messages,
        "max_tokens": 1024,
    }).encode()

    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=body,
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read())
        return data["choices"][0]["message"]["content"]


@app.route("/")
def index():
    return send_from_directory(STATIC_DIR, "index.html")


@app.route("/<path:path>")
def static_files(path):
    full_path = os.path.join(STATIC_DIR, path)
    if os.path.isfile(full_path):
        return send_from_directory(STATIC_DIR, path)
    return send_from_directory(STATIC_DIR, "index.html")


@app.route("/api/agents", methods=["GET"])
def get_agents():
    return jsonify(list(agents.values()))


@app.route("/api/agents", methods=["POST"])
def create_agent():
    data = request.json or {}
    agent_id = str(uuid.uuid4())
    port = data.get("port") or next_port[0]
    next_port[0] = port + 1

    agent = {
        "id": agent_id,
        "name": data.get("name", "Agent"),
        "emoji": data.get("emoji", "🤖"),
        "color": data.get("color", "#6366f1"),
        "personality": data.get("personality", "I am a helpful AI assistant."),
        "capabilities": data.get("capabilities", []),
        "port": port,
        "status": "online",
        "apiKey": data.get("apiKey", ""),
        "model": data.get("model", "gpt-4o-mini"),
    }

    agents[agent_id] = agent
    save_agents()

    if FACTORY_AVAILABLE:
        factory = AgentFactory(os.path.join(BASE_DIR, "generated_agents"))
        factory.create_agent(agent)

    return jsonify(agent), 201


@app.route("/api/agents/<agent_id>", methods=["GET"])
def get_agent(agent_id: str):
    agent = agents.get(agent_id)
    if not agent:
        return jsonify({"error": "Agent not found"}), 404
    return jsonify(agent)


@app.route("/api/agents/<agent_id>", methods=["DELETE"])
def delete_agent(agent_id: str):
    if agent_id not in agents:
        return jsonify({"success": False, "message": "Agent not found"}), 404
    del agents[agent_id]
    save_agents()
    return jsonify({"success": True, "message": "Agent deleted"})


@app.route("/api/agents/<agent_id>/chat", methods=["POST"])
def chat_with_agent(agent_id: str):
    agent = agents.get(agent_id)
    if not agent:
        return jsonify({"error": "Agent not found"}), 404

    data = request.json or {}
    message = data.get("message", "")
    history = data.get("history", [])

    messages = [{"role": m["role"], "content": m["content"]} for m in history]
    messages.append({"role": "user", "content": message})

    try:
        response_text = call_openai(agent, messages)
        return jsonify({
            "message": response_text,
            "agentId": agent["id"],
            "agentName": agent["name"],
            "agentEmoji": agent["emoji"],
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/agents/<agent_id>/tts", methods=["POST"])
def agent_tts(agent_id: str):
    agent = agents.get(agent_id)
    if not agent:
        return jsonify({"error": "Agent not found"}), 404

    data = request.json or {}
    text = data.get("text", "")
    lang = data.get("lang", "en")

    encoded = quote(text[:200])
    audio_url = f"https://translate.google.com/translate_tts?ie=UTF-8&tl={lang}&client=tw-ob&q={encoded}"
    return jsonify({"audioUrl": audio_url, "text": text})


@app.route("/api/rooms", methods=["GET"])
def get_rooms():
    return jsonify(list(rooms.values()))


@app.route("/api/rooms", methods=["POST"])
def create_room():
    data = request.json or {}
    room_id = str(uuid.uuid4())
    room = {
        "id": room_id,
        "name": data.get("name", "Room"),
        "agentIds": data.get("agentIds", []),
        "createdAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    rooms[room_id] = room
    return jsonify(room), 201


@app.route("/api/rooms/<room_id>", methods=["DELETE"])
def delete_room(room_id: str):
    if room_id not in rooms:
        return jsonify({"success": False, "message": "Room not found"}), 404
    del rooms[room_id]
    return jsonify({"success": True, "message": "Room deleted"})


@app.route("/api/rooms/<room_id>/message", methods=["POST"])
def send_room_message(room_id: str):
    room = rooms.get(room_id)
    if not room:
        return jsonify({"error": "Room not found"}), 404

    data = request.json or {}
    message = data.get("message", "")
    from_user = data.get("fromUser", "User")

    room_agents = [agents[aid] for aid in room["agentIds"] if aid in agents]
    agent_names = ", ".join(f"{a['emoji']} {a['name']}" for a in room_agents)
    context_msg = f"[Group chat room '{room['name']}'. Participants: {agent_names}. {from_user} says:] {message}"

    responses = []
    for agent in room_agents:
        try:
            resp = call_openai(agent, [{"role": "user", "content": context_msg}])
            responses.append({
                "agentId": agent["id"],
                "agentName": agent["name"],
                "agentEmoji": agent["emoji"],
                "message": resp,
            })
        except Exception as e:
            responses.append({
                "agentId": agent["id"],
                "agentName": agent["name"],
                "agentEmoji": agent["emoji"],
                "message": f"[{agent['name']} encountered an error: {e}]",
            })

    return jsonify(responses)


@app.route("/terminal/exec", methods=["POST"])
@app.route("/api/terminal/exec", methods=["POST"])
def terminal_exec():
    data = request.json or {}
    command = data.get("command", "")
    pin = data.get("pin", "")
    config = load_config()

    stored_hash = config.get("terminal_pin_hash") or os.environ.get("TERMINAL_PIN_HASH", DEFAULT_PIN_HASH)

    if hash_pin(pin) != stored_hash:
        return jsonify({"error": "Invalid PIN"}), 403

    if is_dangerous(command):
        return jsonify({"output": "", "exitCode": 1, "error": "Dangerous command blocked"}), 403

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=os.environ.get("HOME", "/tmp"),
        )
        output = result.stdout + (f"\nSTDERR:\n{result.stderr}" if result.stderr else "")
        return jsonify({"output": output or "(no output)", "exitCode": result.returncode})
    except subprocess.TimeoutExpired:
        return jsonify({"output": "", "exitCode": 124, "error": "Command timed out"})
    except Exception as e:
        return jsonify({"output": "", "exitCode": 1, "error": str(e)})


@app.route("/tools/sync", methods=["GET"])
@app.route("/api/tools/sync", methods=["GET"])
def sync_tools():
    tools = []
    if os.path.exists(SHARED_TOOLS_DIR):
        tools = [
            os.path.splitext(f)[0]
            for f in os.listdir(SHARED_TOOLS_DIR)
            if f.endswith((".py", ".ts", ".js"))
        ]
    default_tools = ["web_fetch", "terminal_wrapper", "voice_processor"]
    all_tools = list(set(default_tools + tools))
    return jsonify({"tools": all_tools})


if SOCKETIO_AVAILABLE:
    @socketio.on("join_room")
    def handle_join(data):
        room = data.get("room")
        if room:
            join_room(room)
            emit("status", {"msg": f"Joined room {room}"})

    @socketio.on("leave_room")
    def handle_leave(data):
        room = data.get("room")
        if room:
            leave_room(room)

    @socketio.on("group_message")
    def handle_group_message(data):
        room_id = data.get("roomId")
        message = data.get("message", "")
        room = rooms.get(room_id)
        if not room:
            emit("error", {"msg": "Room not found"})
            return

        emit("message", {"from": "User", "content": message}, to=room_id)

        for agent_id in room.get("agentIds", []):
            agent = agents.get(agent_id)
            if agent:
                try:
                    resp = call_openai(agent, [{"role": "user", "content": message}])
                    emit("message", {
                        "from": f"{agent['emoji']} {agent['name']}",
                        "agentId": agent_id,
                        "content": resp,
                        "color": agent.get("color", "#6366f1"),
                    }, to=room_id)
                except Exception as e:
                    emit("error", {"msg": str(e)}, to=room_id)


def main():
    load_agents()
    config = load_config()
    port = config.get("hub_port", int(os.environ.get("PORT", 8080)))

    print(f"""
╔═══════════════════════════════════════════════╗
║          SeVIn AI Hub — Starting Up           ║
╚═══════════════════════════════════════════════╝

  Hub server: http://0.0.0.0:{port}
  Agents loaded: {len(agents)}
  SocketIO: {"enabled" if SOCKETIO_AVAILABLE else "disabled"}
""")

    if SOCKETIO_AVAILABLE:
        socketio.run(app, host="0.0.0.0", port=port, debug=False, allow_unsafe_werkzeug=True)
    else:
        app.run(host="0.0.0.0", port=port, debug=False)


if __name__ == "__main__":
    main()
