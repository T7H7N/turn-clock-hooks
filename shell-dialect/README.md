# Shell dialect

A pipeline such as `Get-Content notes.txt | head -5` fails on a stock Windows shell. The hook points to `Select-Object -First` before the pipeline runs.

It recognizes common POSIX command names at statement boundaries, plus grouped flags on `ls` and `rm`. Quoted text, here-strings and comments are treated as data. Nested executable code in interpolated strings can be missed.

## Registration

Copy this folder to a stable location. Replace `HOOKS_HOME` with the full directory containing this folder, using forward slashes. Merge the entry into the corresponding event array in your host's `settings.json`. Keep the other entries.

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "PowerShell",
        "hooks": [
          {
            "type": "command",
            "command": "python -I -B \"HOOKS_HOME/shell-dialect/hook.py\""
          }
        ]
      }
    ]
  }
}
```

## False positives

A workstation with a native `head` can run that pipeline. Set `SHELL_NATIVE_COMMANDS` to space-separated names such as `head grep` in the host environment to keep those commands available.

## Disable and verify

Remove this command entry from `PreToolUse` in the same settings file. Run `python -B test_hook.py` from this folder to check the hook independently.
