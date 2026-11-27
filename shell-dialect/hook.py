"""Catch common POSIX command forms in a PowerShell tool call."""
import json
import os
import re
import sys


# Keep quoted arguments opaque. Preserve newlines outside comments and literals.
NON_CODE = re.compile(
    r"""(?mx)
    @'(?=\r?$)[\s\S]*?(?:^'@|\Z) | @"(?=\r?$)[\s\S]*?(?:^"@|\Z)
    | <\#[\s\S]*?(?:\#>|\Z) | (?:^|(?<=\s))\#[^\n]*
    | '(?:''|[^'])*(?:'|\Z) | "(?:`[\s\S]|[^"`])*(?:"|\Z) | `[\s\S]
    """
)
HEAD = re.compile(r"(?:^|[;|&({\n])[ \t]*([a-zA-Z]+)(?=[ \t\r\n;|&)]|$)(?:[ \t]+(-[a-zA-Z0-9]+))?")
ALTERNATIVES = {
    "grep": "Select-String", "head": "Select-Object -First",
    "tail": "Select-Object -Last", "wc": "Measure-Object",
    "printf": "the -f format operator", "export": "an environment assignment",
    "source": "dot sourcing",
}


def check(args, data):
    command = args.get("command")
    if not isinstance(command, str):
        return
    accepted = set(os.getenv("SHELL_NATIVE_COMMANDS", "").lower().split())
    text = NON_CODE.sub(lambda m: " " if m[0].lstrip().startswith(("#", "<#")) else "~", command)
    for match in HEAD.finditer(text):
        name, flag = match[1].lower(), match[2] or ""
        if name in accepted:
            continue
        hint = ALTERNATIVES.get(name)
        if name == "ls" and re.fullmatch(r"-(?:[alhtr]{2,}|1)", flag):
            hint = "Get-ChildItem -Force"
        if name == "rm" and flag in ("-rf", "-fr"):
            hint = "Remove-Item with explicit parameters after checking the target"
        if hint:
            return f"'{name}' looks like POSIX syntax. Use {hint}, or choose the Bash tool."



def main():
    try:
        data = json.loads(sys.stdin.buffer.read().decode("utf-8-sig"))
        if not isinstance(data, dict) or data.get("hook_event_name", "PreToolUse") != "PreToolUse":
            return
        args = data.get("tool_input")
        if data.get("tool_name") not in ("PowerShell",) or not isinstance(args, dict):
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
