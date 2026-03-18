#!/usr/bin/env python3
"""
SeVIn AI Hub Setup Wizard
Interactive CLI that collects API keys, terminal PIN, and creates custom agents.
"""

import json
import hashlib
import os
import sys

CAPABILITIES = [
    "web_access",
    "terminal",
    "voice",
    "image_gen",
    "file_edit",
    "group_chat",
]

AGENTS_FILE = os.path.join(os.path.dirname(__file__), "agents.json")
CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config.json")

def hash_pin(pin: str) -> str:
    return hashlib.sha256(pin.encode()).hexdigest()

def clear():
    os.system("cls" if os.name == "nt" else "clear")

def banner():
    print("""
╔═══════════════════════════════════════════════╗
║          SeVIn AI Hub — Setup Wizard          ║
║     Multi-Agent AI System Configuration       ║
╚═══════════════════════════════════════════════╝
""")

def ask(prompt: str, default: str = "") -> str:
    if default:
        response = input(f"{prompt} [{default}]: ").strip()
        return response if response else default
    return input(f"{prompt}: ").strip()

def ask_int(prompt: str, default: int) -> int:
    while True:
        try:
            val = input(f"{prompt} [{default}]: ").strip()
            return int(val) if val else default
        except ValueError:
            print("  Please enter a valid number.")

def ask_yes_no(prompt: str, default: bool = True) -> bool:
    default_str = "Y/n" if default else "y/N"
    while True:
        val = input(f"{prompt} [{default_str}]: ").strip().lower()
        if not val:
            return default
        if val in ("y", "yes"):
            return True
        if val in ("n", "no"):
            return False
        print("  Please enter y or n.")

def pick_capabilities() -> list[str]:
    print("\n  Available capabilities:")
    for i, cap in enumerate(CAPABILITIES, 1):
        print(f"    {i}. {cap}")
    print("  Enter numbers separated by commas (e.g. 1,3,5) or 'all'")
    while True:
        val = input("  Select capabilities: ").strip().lower()
        if val == "all":
            return list(CAPABILITIES)
        try:
            indices = [int(x.strip()) for x in val.split(",")]
            selected = [CAPABILITIES[i - 1] for i in indices if 1 <= i <= len(CAPABILITIES)]
            if selected:
                return selected
        except (ValueError, IndexError):
            pass
        print("  Invalid selection, try again.")

def create_agent(next_port: int) -> dict:
    print("\n─── New Agent Configuration ───────────────────")
    name = ask("  Agent name")
    while not name:
        print("  Name is required.")
        name = ask("  Agent name")

    emoji = ask("  Agent emoji", "🤖")
    color = ask("  Agent color (hex)", "#6366f1")
    if not color.startswith("#"):
        color = "#" + color

    print(f"  Personality (describe how {name} behaves, press Enter twice when done):")
    lines = []
    while True:
        line = input("  > ")
        if not line and lines:
            break
        lines.append(line)
    personality = " ".join(lines) or f"I am {name}, a helpful AI assistant."

    caps = pick_capabilities()
    port = ask_int("  Port number", next_port)
    api_key = ask("  OpenAI API key (leave blank to use global key)", "")
    model = ask("  Model (e.g. gpt-4o, gpt-4o-mini)", "gpt-4o-mini")

    return {
        "name": name,
        "emoji": emoji,
        "color": color,
        "personality": personality,
        "capabilities": caps,
        "port": port,
        "status": "offline",
        "apiKey": api_key,
        "model": model,
    }

def setup_global_config() -> dict:
    print("\n─── Global Configuration ────────────────────────")
    api_key = ask("  Global OpenAI API key (all agents will use this unless overridden)", "")

    print("\n  Terminal PIN (4-digit number for secure command execution)")
    while True:
        pin = input("  Enter PIN [1234]: ").strip() or "1234"
        if pin.isdigit() and len(pin) >= 4:
            break
        print("  PIN must be at least 4 digits.")

    pin_hash = hash_pin(pin)

    hub_port = ask_int("  Hub server port", 8080)

    return {
        "global_api_key": api_key,
        "terminal_pin_hash": pin_hash,
        "hub_port": hub_port,
    }

def main():
    clear()
    banner()
    print("Welcome! This wizard will configure your SeVIn AI Hub.\n")

    global_config = setup_global_config()
    agents = []
    next_port = 8001

    print("\n─── Agent Creation ──────────────────────────────")
    print("Now let's create your AI agents. You can create as many as you want.\n")

    while True:
        agent_data = create_agent(next_port)
        agents.append(agent_data)
        next_port = agent_data["port"] + 1

        print(f"\n  ✓ Agent '{agent_data['emoji']} {agent_data['name']}' created on port {agent_data['port']}")
        print(f"    Capabilities: {', '.join(agent_data['capabilities'])}")

        if not ask_yes_no("\n  Add another agent?", default=False):
            break

    os.makedirs(os.path.dirname(AGENTS_FILE), exist_ok=True)

    with open(AGENTS_FILE, "w") as f:
        json.dump(agents, f, indent=2)
    print(f"\n  ✓ Saved {len(agents)} agent(s) to {AGENTS_FILE}")

    with open(CONFIG_FILE, "w") as f:
        json.dump(global_config, f, indent=2)
    print(f"  ✓ Saved configuration to {CONFIG_FILE}")

    print("\n─── Setup Complete ──────────────────────────────")
    print(f"\n  Created {len(agents)} agent(s):")
    for agent in agents:
        print(f"    {agent['emoji']} {agent['name']} → port {agent['port']}")

    print(f"\n  Hub will run on port {global_config['hub_port']}")
    print("\n  Next steps:")
    print("    1. Run: bash wizard.sh     (to install deps and launch)")
    print("    2. Or:  python launch_system.py --start")
    print("\n  SeVIn AI Hub is ready to launch! 🚀\n")

if __name__ == "__main__":
    main()
