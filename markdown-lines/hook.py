"""Report long physical lines after a complete Markdown write."""
import json
import os
import re
import sys


def check(args, data):
    path, content = args.get("file_path"), args.get("content")
    if not isinstance(path, str) or not path.lower().endswith((".md", ".markdown")):
        return
    if not isinstance(content, str):
        return
    try:
        limit = int(os.getenv("MARKDOWN_LINE_LIMIT", "1500"))
    except ValueError:
        limit = 1500
    if limit < 1:
        limit = 1500
    count = longest = 0
    for line in re.finditer(r"[^\r\n]+", content):
        width = line.end() - line.start()
        if width > limit:
            count += 1
            longest = max(longest, width)
    if count:
        return f"{count} Markdown line(s) exceed {limit} characters. Longest line: {longest}."


def main():
    try:
        data = json.loads(sys.stdin.buffer.read().decode("utf-8-sig"))
        if not isinstance(data, dict) or data.get("hook_event_name", "PostToolUse") != "PostToolUse":
            return
        args = data.get("tool_input")
        if data.get("tool_name") not in ("Write",) or not isinstance(args, dict):
            return
        message = check(args, data)
    except (ValueError, OSError, RecursionError):
        return
    if message:
        print(json.dumps({"hookSpecificOutput": {
            "hookEventName": "PostToolUse",
            "additionalContext": message,
        }}))


if __name__ == "__main__":
    main()
