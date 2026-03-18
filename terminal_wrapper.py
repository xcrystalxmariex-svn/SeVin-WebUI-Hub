import subprocess
import hashlib
import os
import re
import signal
from typing import Optional

DANGEROUS_PATTERNS = [
    r"rm\s+-rf\s+/",
    r"mkfs",
    r"dd\s+if=/dev/zero",
    r":\(\)\{\s*:\|:&\s*\};:",
    r"chmod\s+777\s+/",
    r">\s*/dev/sda",
    r"format\s+[a-z]:",
    r"del\s+/f\s+/s\s+/q",
    r"shutdown\s+-h\s+now",
    r"reboot",
    r"init\s+0",
    r"halt",
]

DEFAULT_PIN_HASH = "03ac674216f3e15c761ee1a5e255f067953623c8b388b4459e13f978d7c846f4"

def hash_pin(pin: str) -> str:
    return hashlib.sha256(pin.encode()).hexdigest()

def verify_pin(pin: str, stored_hash: Optional[str] = None) -> bool:
    if stored_hash is None:
        stored_hash = os.environ.get("TERMINAL_PIN_HASH", DEFAULT_PIN_HASH)
    return hash_pin(pin) == stored_hash

def is_dangerous(command: str) -> tuple[bool, str]:
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, command, re.IGNORECASE):
            return True, f"Command matches dangerous pattern: {pattern}"
    return False, ""

def execute_command(
    command: str,
    pin: str,
    timeout: int = 30,
    working_dir: Optional[str] = None,
    stored_pin_hash: Optional[str] = None,
) -> dict:
    if not verify_pin(pin, stored_pin_hash):
        return {
            "success": False,
            "output": "",
            "error": "Invalid PIN. Access denied.",
            "exit_code": 1,
            "blocked": False,
        }

    dangerous, reason = is_dangerous(command)
    if dangerous:
        return {
            "success": False,
            "output": "",
            "error": f"Command blocked for safety: {reason}",
            "exit_code": 1,
            "blocked": True,
        }

    cwd = working_dir or os.environ.get("HOME", "/tmp")

    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
            env={**os.environ, "TERM": "xterm"},
        )

        output = result.stdout
        if result.stderr:
            output += f"\nSTDERR:\n{result.stderr}"

        return {
            "success": result.returncode == 0,
            "output": output or "(no output)",
            "error": None,
            "exit_code": result.returncode,
            "blocked": False,
        }

    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "output": "",
            "error": f"Command timed out after {timeout} seconds",
            "exit_code": 124,
            "blocked": False,
        }
    except Exception as e:
        return {
            "success": False,
            "output": "",
            "error": f"Execution error: {e}",
            "exit_code": 1,
            "blocked": False,
        }


if __name__ == "__main__":
    pin = "1234"
    result = execute_command("echo 'Hello from SeVIn Terminal'", pin=pin)
    print(f"Success: {result['success']}")
    print(f"Output: {result['output']}")
