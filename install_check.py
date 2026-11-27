"""Validate the documented registrations, then time 20 fresh processes per hook."""
import argparse
import json
import os
from pathlib import Path
import re
import shlex
import statistics
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parent
SPECS = {
    ("turn-clock", "UserPromptSubmit"): (None, {}),
    ("turn-clock", "PostToolBatch"): (None, {}),
    ("shell-dialect", "PreToolUse"): ("PowerShell", {"command": "ls -la"}),
    ("inline-path", "PreToolUse"): ("Bash", {"command": "printf '%s' 'Q:" + "\\" * 2 + "tab'"}),
    ("script-bom", "PostToolUse"): ("Write|Edit", {"file_path": "example.ps1"}),
    ("markdown-lines", "PostToolUse"): ("Write", {"file_path": "example.md", "content": "a" * 1501}),
    ("read-window", "PreToolUse"): ("Read", {"file_path": "example.log"}),
}
REPEATS = 20
BUDGET = 0.5


def registrations(readme):
    blocks = re.findall(r"^```json\n(.*?)^```$", readme.read_text(encoding="utf-8"), re.M | re.S)
    if len(blocks) != 1:
        raise ValueError(f"Expected one JSON settings example in {readme.name}")
    result = {}
    for event, groups in json.loads(blocks[0])["hooks"].items():
        for group in groups:
            for handler in group["hooks"]:
                words = shlex.split(handler["command"])
                if handler["type"] != "command" or len(words) != 4 or words[:3] != ["python", "-I", "-B"]:
                    raise ValueError(f"Unexpected hook command in {readme.name}")
                target = words[3].split("/")
                if len(target) != 3 or target[0] != "HOOKS_HOME" or target[2] != "hook.py":
                    raise ValueError("Expected a hook under HOOKS_HOME")
                name = target[1]
                key = (name, event)
                if key not in SPECS or key in result:
                    raise ValueError(f"Unknown or duplicate registration: {name}")
                result[key] = (group.get("matcher"), [sys.executable, *words[1:3], str(ROOT / name / target[2])])
    return result


def run(enforce_budget=True):
    root_entries = registrations(ROOT / "README.md")
    if set(root_entries) != set(SPECS):
        raise ValueError("Collection registration does not cover every hook")
    env = os.environ.copy()
    for key in ("SHELL_NATIVE_COMMANDS", "MARKDOWN_LINE_LIMIT", "READ_WINDOW_KIB", "TURN_CLOCK_LANG", "TURN_CLOCK_ZONE"):
        env.pop(key, None)
    slow = False
    with tempfile.TemporaryDirectory() as temp:
        folder = Path(temp).resolve()
        (folder / "example.ps1").write_bytes("echo caf\u00e9".encode())
        (folder / "example.log").write_bytes(b"a" * 49152)
        for name in sorted({name for name, event in SPECS}):
            single = registrations(ROOT / name / "README.md")
            if single != {key: value for key, value in root_entries.items() if key[0] == name}:
                raise ValueError(f"Conflicting registration: {name}")
        for key, (matcher, args) in SPECS.items():
            name, event = key
            documented_matcher, command = root_entries[key]
            if documented_matcher != matcher:
                raise ValueError(f"Conflicting matcher: {name} {event}")
            data = {"hook_event_name": event, "cwd": str(folder)}
            if matcher is not None:
                data.update(tool_name=matcher.split("|")[0], tool_input=args)
            payload = json.dumps(data).encode("utf-8")
            times = []
            for _ in range(REPEATS):
                start = time.perf_counter()
                proc = subprocess.run(command, input=payload, capture_output=True,
                                      timeout=10, cwd=folder, env=env)
                times.append(time.perf_counter() - start)
                proc.check_returncode()
                reply = json.loads(proc.stdout)["hookSpecificOutput"]
                if proc.stderr or reply["hookEventName"] != event:
                    raise ValueError(f"Unexpected reply: {name}")
                if event == "PreToolUse":
                    if reply.get("permissionDecision") != "deny" or not reply.get("permissionDecisionReason"):
                        raise ValueError(f"Expected denial: {name}")
                elif not reply.get("additionalContext") or "permissionDecision" in reply:
                    raise ValueError(f"Expected advisory: {name}")
            passed = sum(t < BUDGET for t in times)
            slow |= passed != REPEATS
            print(f"{name:16} {event:16} {passed}/{REPEATS} under 500 ms  "
                  f"median {1000 * statistics.median(times):7.2f} ms  max {1000 * max(times):7.2f} ms")
    return int(slow and enforce_budget)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--report-timing", action="store_true", help="report timings without enforcing the latency budget")
    sys.exit(run(enforce_budget=not parser.parse_args().report_timing))
