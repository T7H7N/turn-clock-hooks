"""Inspect the bytes of the script just saved for legacy shell readers."""
import codecs
import json
from pathlib import Path
import stat
import sys


MAX_BYTES = 2 * 1024 * 1024


def check(args, data):
    name = args.get("file_path")
    cwd = data.get("cwd", ".")
    if not isinstance(name, str) or not isinstance(cwd, str):
        return
    path = Path(cwd) / name
    if path.suffix.lower() not in (".ps1", ".psm1", ".psd1"):
        return
    info = path.stat()
    if not stat.S_ISREG(info.st_mode) or info.st_size > MAX_BYTES:
        return
    with path.open("rb") as stream:
        raw = stream.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES or raw.startswith((codecs.BOM_UTF8, codecs.BOM_UTF16_LE,
                                                codecs.BOM_UTF16_BE, codecs.BOM_UTF32_BE)):
        return
    if b"\0" in raw or raw.isascii():
        return
    try:
        raw.decode("utf-8")
    except UnicodeDecodeError:
        return "Unknown script encoding. Check the saved bytes before converting this script."
    return ("Non-ASCII UTF-8 script without a BOM. If it runs under Windows PowerShell "
            "5.1, save as UTF-8 with BOM to preserve its text.")


def main():
    try:
        data = json.loads(sys.stdin.buffer.read().decode("utf-8-sig"))
        if not isinstance(data, dict) or data.get("hook_event_name", "PostToolUse") != "PostToolUse":
            return
        args = data.get("tool_input")
        if data.get("tool_name") not in ("Write", "Edit") or not isinstance(args, dict):
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
