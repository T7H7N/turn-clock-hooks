# Read window

An unbounded Read of a large log can consume the context needed for the investigation. The hook asks for an explicit line count before the read. An offset on its own still leaves the request open-ended.

For common text formats the hook checks file size using metadata alone. At or above `READ_WINDOW_KIB` (default and fallback 48 KiB) a positive integer `limit` allows the request to continue. See `TEXT` in `hook.py` for the extensions. Missing files and unlisted formats pass.

## Registration

Copy this folder to a stable location. Replace `HOOKS_HOME` with the full directory containing this folder, using forward slashes. Merge the entry into the corresponding event array in your host's `settings.json`. Keep the other entries.

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Read",
        "hooks": [
          {
            "type": "command",
            "command": "python -I -B \"HOOKS_HOME/read-window/hook.py\""
          }
        ]
      }
    ]
  }
}
```

## False positives

A host may already truncate a long log, or the caller may need every line. Supply the intended line count or raise the file-size threshold. A single unusually long line can still produce a large response.

## Disable and verify

Remove this command entry from `PreToolUse` in the same settings file. Run `python -B test_hook.py` from this folder to check the hook independently.
