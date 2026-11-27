# Script BOM

A script containing `café` is saved as UTF-8 without a byte-order mark. Windows PowerShell 5.1 can interpret those bytes using a legacy code page. The hook reports the saved encoding after Write or Edit.

It reads only the named regular `.ps1`, `.psm1` or `.psd1` file, up to 2 MiB. ASCII, recognized signatures and NUL-containing data stay quiet. Unknown non-ASCII encodings get a manual inspection message. Another writer can change the bytes before inspection. The hook leaves the file untouched.

## Registration

Copy this folder to a stable location. Replace `HOOKS_HOME` with the full directory containing this folder, using forward slashes. Merge the entry into the corresponding event array in your host's `settings.json`. Keep the other entries.

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write|Edit",
        "hooks": [
          {
            "type": "command",
            "command": "python -I -B \"HOOKS_HOME/script-bom/hook.py\""
          }
        ]
      }
    ]
  }
}
```

## False positives

A script used only with a modern UTF-8 reader can intentionally omit the mark. Enable this hook in projects that also serve legacy readers.

## Disable and verify

Remove this command entry from `PostToolUse` in the same settings file. Run `python -B test_hook.py` from this folder to check the hook independently.
