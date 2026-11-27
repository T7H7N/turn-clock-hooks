"""Flag doubled path separators in shell-embedded code or formatted text."""
import json
import re
import sys


PATH = re.compile(r"(?<![\w\\])(?:[A-Za-z]:\\{2,}|\\{2,}[\w.-]{3,}\\+)[^\s\\'\"]")
RUNNER = re.compile(r"(?:^|[^\w.-])(?:python(?:3(?:\.\d+)?)?w?|py)(?:\.exe)?(?=[\"'\s]|$)", re.I)
CODE_FLAG = re.compile(r"(?:^|\s)-[A-Za-z]*c(?=[\s'\"]|$)")
FORMAT = re.compile(r"(?:^|[\s;(`|&])printf\s")
# Match quoted or escaped content before splitting on an unquoted separator.
SHELL_TOKENS = re.compile(r"""'[^']*(?:'|$)|"(?:\\[\s\S]|[^"\\])*(?:"|\\?$)|\\[\s\S]|[\n;&|]""")


def statements(command):
    start = 0
    for token in SHELL_TOKENS.finditer(command):
        if token[0] in ("\n", ";", "&", "|"):
            yield command[start:token.start()]
            start = token.end()
    yield command[start:]


def check(args, data):
    command = args.get("command")
    if not isinstance(command, str) or not PATH.search(command):
        return
    message = ("A doubled path separator in inline text can change during shell or "
               "interpreter parsing. Use forward slashes or put the code in a file.")
    if "<<" in command:
        return message
    joined = command.replace("\\\r\n", " ").replace("\\\n", " ")
    for part in statements(joined):
        if not PATH.search(part):
            continue
        if FORMAT.search(part):
            return message
        runner = RUNNER.search(part)
        if runner and CODE_FLAG.search(part, runner.end()):
            return message


def main():
    try:
        data = json.loads(sys.stdin.buffer.read().decode("utf-8-sig"))
        if not isinstance(data, dict) or data.get("hook_event_name", "PreToolUse") != "PreToolUse":
            return
        args = data.get("tool_input")
        if data.get("tool_name") not in ("Bash",) or not isinstance(args, dict):
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
