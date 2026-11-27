"""Table-driven checks through the command entry point."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

EVENT = "PreToolUse"
TOOL = "PowerShell"
HOOK = Path(__file__).with_name("hook.py").resolve()


def cases(folder):
    return [
        ("pipeline", {"command": "Get-Content notes | grep blue"}, "deny"),
        ("list flags", {"command": "ls -lah"}, "deny"),
        ("native parameter", {"command": "ls -Recurse"}, ""),
        ("nested argument", {"command": "git grep blue"}, ""),
        ("quoted command in prose", {"command": """Write-Output 'x; head sample'"""}, ""),
        ("block comment", {"command": "<#\nhead sample\n#> Get-Date"}, ""),
        ("here string", {"command": "@'\r\nhead data\r\n'@"}, ""),
        ("line comment", {"command": "Get-Date # x; head data"}, ""),
        ("later command", {"command": "echo done\nwc -l notes"}, "deny"),
        ("configured native", {"command": "grep blue"}, "", {"SHELL_NATIVE_COMMANDS": "grep"}),
        ("invalid command", {"command": 12}, ""),
    ]


def run():
    with tempfile.TemporaryDirectory() as temp:
        folder = Path(temp)
        rows = cases(folder)
        env = os.environ.copy()
        env.pop("SHELL_NATIVE_COMMANDS", None)
        checks = []
        for label, args, expected, *options in rows:
            settings = options[0] if options else {}
            tool = options[1] if len(options) > 1 else TOOL
            payload = {"hook_event_name": EVENT, "tool_name": tool, "cwd": temp, "tool_input": args}
            checks.append((label, json.dumps(payload).encode(), expected, settings))
        for field in ("tool_name", "hook_event_name"):
            payload = {"hook_event_name": EVENT, "tool_name": TOOL, "cwd": temp, "tool_input": rows[0][1]}
            payload[field] = "Other"
            checks.append(("different " + field, json.dumps(payload).encode(), "", {}))
        checks.extend((label, raw, "", {}) for label, raw in [
            ("malformed JSON", b"{"), ("null input", b"null"), ("non-UTF input", b"\xff")
        ])
        for label, raw, expected, settings in checks:
            proc = subprocess.run([sys.executable, "-I", "-B", str(HOOK)], input=raw,
                                  capture_output=True, cwd=temp, env=env | settings, timeout=5)
            if proc.returncode or proc.stderr:
                raise AssertionError((label, proc.returncode, proc.stderr))
            if expected:
                reply = json.loads(proc.stdout)["hookSpecificOutput"]
                assert reply["hookEventName"] == EVENT, label
                if expected == "deny":
                    assert reply["permissionDecision"] == "deny" and reply["permissionDecisionReason"], label
                else:
                    assert "permissionDecision" not in reply and expected in reply["additionalContext"], label
            else:
                assert proc.stdout == b"", label
        print(f"{len(checks)}/{len(checks)} cases passed")


if __name__ == "__main__":
    run()
