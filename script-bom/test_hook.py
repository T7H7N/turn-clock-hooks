"""Table-driven checks through the command entry point."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

EVENT = "PostToolUse"
TOOL = "Write"
HOOK = Path(__file__).with_name("hook.py").resolve()


def cases(folder):
    blobs = {
        "plain.ps1": b"echo ok\r\n", "accent.ps1": "echo caf\u00e9\r\n".encode(),
        "marked.psm1": b"\xef\xbb\xbf" + "caf\u00e9".encode(),
        "legacy.psd1": b"caf\xe9", "wide.ps1": "wide".encode("utf-16"),
        "other.txt": "caf\u00e9".encode(), "empty.ps1": b"",
        "huge.ps1": b"a" * (2 * 1024 * 1024) + b"\xff",
        "nul.ps1": b"a\0\xff", "mixed.PS1": "caf\u00e9".encode(),
    }
    for name, raw in blobs.items():
        (folder / name).write_bytes(raw)
    return [
        ("ASCII", {"file_path": "plain.ps1"}, ""),
        ("missing signature", {"file_path": "accent.ps1"}, "BOM"),
        ("Edit", {"file_path": "mixed.PS1"}, "BOM", {}, "Edit"),
        ("marked", {"file_path": "marked.psm1"}, ""),
        ("unknown encoding", {"file_path": "legacy.psd1"}, "Unknown"),
        ("wide encoding", {"file_path": "wide.ps1"}, ""),
        ("different extension", {"file_path": "other.txt"}, ""),
        ("empty file", {"file_path": "empty.ps1"}, ""),
        ("size cap", {"file_path": "huge.ps1"}, ""),
        ("binary", {"file_path": "nul.ps1"}, ""),
        ("missing", {"file_path": "absent.ps1"}, ""),
    ]


def run():
    with tempfile.TemporaryDirectory() as temp:
        folder = Path(temp)
        rows = cases(folder)
        env = os.environ.copy()

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
