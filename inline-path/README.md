# Inline path

A code generator sends a drive path with doubled backslashes through `python -c`. If one quoting layer collapses the separators, the interpreter can turn a directory beginning with `t` into a tab. Use forward slashes in the embedded path or write the script to a file.

The check looks for a drive or share prefix along with a here-document, `printf`, or an inline Python command. Ordinary script invocations and single separators pass. It uses textual patterns and does not parse arbitrary Bash or prove the resulting bytes.

## Registration

Copy this folder to a stable location. Replace `HOOKS_HOME` with the full directory containing this folder, using forward slashes. Merge the entry into the corresponding event array in your host's `settings.json`. Keep the other entries.

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "python -I -B \"HOOKS_HOME/inline-path/hook.py\""
          }
        ]
      }
    ]
  }
}
```

## False positives

A double-quoted argument to `printf '%s'` may already preserve the intended bytes. A here-document in another part of the same command can also trigger a warning about a harmless path. Rewrite the path with forward slashes or remove the entry when this workflow is intentional.

## Disable and verify

Remove this command entry from `PreToolUse` in the same settings file. Run `python -B test_hook.py` from this folder to check the hook independently.
