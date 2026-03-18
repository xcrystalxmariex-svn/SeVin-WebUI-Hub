#!/usr/bin/env python3
"""
SeVIn AI Hub — Launch System Manager
Manages tmux sessions for the hub and all agents.
"""

import argparse
import json
import os
import subprocess
import sys
import time

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
AGENTS_FILE = os.path.join(BASE_DIR, "agents.json")
CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
SESSION_NAME = "sevin-hub"


def run(cmd: str, capture: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, shell=True, capture_output=capture, text=True)


def tmux(cmd: str) -> subprocess.CompletedProcess:
    return run(f"tmux {cmd}", capture=True)


def session_exists() -> bool:
    result = tmux(f"has-session -t {SESSION_NAME}")
    return result.returncode == 0


def load_agents() -> list[dict]:
    if not os.path.exists(AGENTS_FILE):
        return []
    with open(AGENTS_FILE) as f:
        return json.load(f)


def load_config() -> dict:
    if not os.path.exists(CONFIG_FILE):
        return {}
    with open(CONFIG_FILE) as f:
        return json.load(f)


def start():
    if session_exists():
        print(f"Session '{SESSION_NAME}' already running. Use --stop first.")
        return

    agents = load_agents()
    config = load_config()
    hub_port = config.get("hub_port", 8080)

    print(f"Starting SeVIn AI Hub on port {hub_port}...")

    tmux(f"new-session -d -s {SESSION_NAME} -n hub")
    hub_cmd = f"cd '{BASE_DIR}' && python hub_server.py"
    tmux(f"send-keys -t {SESSION_NAME}:hub '{hub_cmd}' Enter")

    for i, agent in enumerate(agents, 1):
        safe_name = agent["name"].replace(" ", "_").replace("-", "_").lower()
        agent_file = os.path.join(BASE_DIR, "generated_agents", f"{safe_name}_main.py")
        window_name = f"agent-{i}"

        tmux(f"new-window -t {SESSION_NAME} -n {window_name}")

        if os.path.exists(agent_file):
            cmd = f"cd '{BASE_DIR}' && python '{agent_file}'"
        else:
            cmd = f"echo 'Agent file not found: {agent_file}'"

        tmux(f"send-keys -t {SESSION_NAME}:{window_name} '{cmd}' Enter")
        print(f"  Started {agent['emoji']} {agent['name']} (port {agent['port']}) in window {window_name}")

    print(f"\n✓ SeVIn AI Hub running in tmux session '{SESSION_NAME}'")
    print(f"  Hub:    http://localhost:{hub_port}")
    print(f"\n  Attach: tmux attach -t {SESSION_NAME}")
    print(f"  Stop:   python launch_system.py --stop")


def stop():
    if not session_exists():
        print(f"No session '{SESSION_NAME}' found.")
        return

    tmux(f"kill-session -t {SESSION_NAME}")
    print(f"✓ Stopped session '{SESSION_NAME}'")


def status():
    if not session_exists():
        print(f"Session '{SESSION_NAME}': not running")
        return

    print(f"Session '{SESSION_NAME}': running")
    result = tmux(f"list-windows -t {SESSION_NAME}")
    if result.stdout:
        print("\nWindows:")
        for line in result.stdout.strip().split("\n"):
            print(f"  {line}")


def add_agent(name: str, emoji: str = "🤖", color: str = "#6366f1",
              personality: str = "", capabilities: list[str] = None,
              port: int = None, model: str = "gpt-4o-mini"):
    agents = load_agents()
    used_ports = {a["port"] for a in agents}
    if port is None:
        port = 8001
        while port in used_ports:
            port += 1

    import uuid
    agent = {
        "id": str(uuid.uuid4()),
        "name": name,
        "emoji": emoji,
        "color": color,
        "personality": personality or f"I am {name}, a helpful AI assistant.",
        "capabilities": capabilities or ["group_chat"],
        "port": port,
        "status": "offline",
        "model": model,
    }
    agents.append(agent)

    with open(AGENTS_FILE, "w") as f:
        json.dump(agents, f, indent=2)

    print(f"✓ Agent '{emoji} {name}' added on port {port}")

    try:
        sys.path.insert(0, BASE_DIR)
        from agent_factory import AgentFactory
        factory = AgentFactory(os.path.join(BASE_DIR, "generated_agents"))
        factory.create_agent(agent)
        print(f"✓ Agent file generated")
    except Exception as e:
        print(f"Warning: Could not generate agent file: {e}")

    if session_exists():
        agent_count = len(agents)
        safe_name = name.replace(" ", "_").replace("-", "_").lower()
        agent_file = os.path.join(BASE_DIR, "generated_agents", f"{safe_name}_main.py")
        window_name = f"agent-{agent_count}"
        tmux(f"new-window -t {SESSION_NAME} -n {window_name}")
        if os.path.exists(agent_file):
            cmd = f"cd '{BASE_DIR}' && python '{agent_file}'"
            tmux(f"send-keys -t {SESSION_NAME}:{window_name} '{cmd}' Enter")
            print(f"✓ Started new agent in window {window_name}")


def main():
    parser = argparse.ArgumentParser(description="SeVIn AI Hub Launch System")
    parser.add_argument("--start", action="store_true", help="Start all services")
    parser.add_argument("--stop", action="store_true", help="Stop all services")
    parser.add_argument("--status", action="store_true", help="Show status")
    parser.add_argument("--add-agent", metavar="NAME", help="Add a new agent")
    parser.add_argument("--emoji", default="🤖")
    parser.add_argument("--color", default="#6366f1")
    parser.add_argument("--personality", default="")
    parser.add_argument("--capabilities", nargs="+",
                        choices=["web_access", "terminal", "voice", "image_gen", "file_edit", "group_chat"])
    parser.add_argument("--port", type=int)
    parser.add_argument("--model", default="gpt-4o-mini")

    args = parser.parse_args()

    if args.start:
        start()
    elif args.stop:
        stop()
    elif args.status:
        status()
    elif args.add_agent:
        add_agent(
            args.add_agent,
            emoji=args.emoji,
            color=args.color,
            personality=args.personality,
            capabilities=args.capabilities,
            port=args.port,
            model=args.model,
        )
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
