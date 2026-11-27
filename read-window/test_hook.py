"""Table-driven checks through the command entry point."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

EVENT = "PreToolUse"
TOOL = "Read"
HOOK = Path(__file__).with_name("hook.py").resolve()


def cases(folder):
    for name, size in (("small.txt", 49151), ("edge.txt", 49152),
                       ("big.log", 70000), ("image.png", 70000)):
        (folder / name).write_bytes(b"a" * size)
    return [
        ("below limit", {"file_path": "small.txt"}, ""),
        ("at limit", {"file_path": "edge.txt"}, "deny"),
        ("over limit", {"file_path": "big.log"}, "deny"),
        ("window", {"file_path": "big.log", "offset": 2, "limit": 3}, ""),
        ("offset only", {"file_path": "big.log", "offset": 2}, "deny"),
        ("zero window", {"file_path": "big.log", "limit": 0}, "deny"),
        ("boolean window", {"file_path": "big.log", "limit": True}, "deny"),
        ("other type", {"file_path": "image.png"}, ""),
        ("missing", {"file_path": "gone.md"}, ""),
        ("configured limit", {"file_path": "big.log"}, "", {"READ_WINDOW_KIB": "96"}),
        ("invalid setting", {"file_path": "big.log"}, "deny", {"READ_WINDOW_KIB": "no"}),
    ]


def run():
    with tempfile.TemporaryDirectory() as temp:
        folder = Path(temp)
        rows = cases(folder)
        env = os.environ.copy()
        env.pop("READ_WINDOW_KIB", None)
        checks = []
        for label, args, expected, *options in rows:
            settings = options[0] if options else {}
            tool = options[1] if len(options) > 1 else TOOL
            payload = {"hook_event_name": EVENT, "tool_name": tool, "cwd": temp, "tool_input": args}
            checks.append((label, json.dumps(payload).encode(), expected, settings))
        for field in ("tool_name", "hook_event_name"):
            payload = {"hook_event_name": EVENT, "tool_name": TOOL, "cwd": temp, "tool_input": rows[1][1]}
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
