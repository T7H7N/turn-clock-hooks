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
    def entry(text, name="notes.md"):
        return {"file_path": name, "content": text}

    return [
        ("at limit", entry("a" * 1500), ""),
        ("past limit", entry("a" * 1501), "Longest line: 1501"),
        ("mixed endings", entry("abc\r\nabcd\rxy\n12345"), "2 Markdown line(s) exceed 3 characters. Longest line: 5", {"MARKDOWN_LINE_LIMIT": "3"}),
        ("code points", entry("\U0001f680" * 3), "", {"MARKDOWN_LINE_LIMIT": "3"}),
        ("other type", entry("a" * 1501, "data.csv"), ""),
        ("alternate extension", entry("a" * 1501, "notes.MARKDOWN"), "1501"),
        ("empty", entry(""), ""),
        ("invalid setting", entry("a" * 1500), "", {"MARKDOWN_LINE_LIMIT": "zero"}),
        ("nonpositive setting", entry("a" * 1501), "exceed 1500", {"MARKDOWN_LINE_LIMIT": "0"}),
        ("no content", {"file_path": "notes.md"}, ""),
    ]


def run():
    with tempfile.TemporaryDirectory() as temp:
        folder = Path(temp)
        rows = cases(folder)
        env = os.environ.copy()
        env.pop("MARKDOWN_LINE_LIMIT", None)
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
