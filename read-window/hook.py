"""Ask for a line window when opening a large text file."""
import json
import os
from pathlib import Path
import stat
import sys


TEXT = {".txt", ".log", ".md", ".csv", ".tsv", ".json", ".jsonl",
        ".xml", ".yaml", ".yml", ".py", ".js", ".ts", ".html", ".css"}


def check(args, data):
    count = args.get("limit")
    if type(count) is int and count > 0:
        return
    name, cwd = args.get("file_path"), data.get("cwd", ".")
    if not isinstance(name, str) or not isinstance(cwd, str):
        return
    path = Path(cwd) / name
    if path.suffix.lower() not in TEXT:
        return
    try:
        limit = int(os.getenv("READ_WINDOW_KIB", "48"))
    except ValueError:
        limit = 48
    if limit < 1:
        limit = 48
    info = path.stat()
    if stat.S_ISREG(info.st_mode) and info.st_size >= limit * 1024:
        return (f"The file is {info.st_size} bytes. Choose a starting line with offset "
                "and a positive line count with limit before reading it.")


def main():
    try:
        data = json.loads(sys.stdin.buffer.read().decode("utf-8-sig"))
        if not isinstance(data, dict) or data.get("hook_event_name", "PreToolUse") != "PreToolUse":
            return
        args = data.get("tool_input")
        if data.get("tool_name") not in ("Read",) or not isinstance(args, dict):
            return
        message = check(args, data)
    except (ValueError, OSError, RecursionError):
        return
    if message:
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": message,
        }}))


if __name__ == "__main__":
    main()
