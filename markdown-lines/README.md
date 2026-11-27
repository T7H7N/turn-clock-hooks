# Markdown lines

A report generator writes a whole Markdown chapter on one physical line. The saved document looks fine when wrapped, but a line-based diff replaces the whole chapter. The hook reports the number of long lines and their maximum length.

After a full Write, it counts Unicode code points in each line of the submitted `.md` or `.markdown` content. CR, LF and CRLF end a line. Set `MARKDOWN_LINE_LIMIT` to a positive integer. The default and fallback are 1500. The count excludes line endings.

## Registration

Copy this folder to a stable location. Replace `HOOKS_HOME` with the full directory containing this folder, using forward slashes. Merge the entry into the corresponding event array in your host's `settings.json`. Keep the other entries.

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write",
        "hooks": [
          {
            "type": "command",
            "command": "python -I -B \"HOOKS_HOME/markdown-lines/hook.py\""
          }
        ]
      }
    ]
  }
}
```

## False positives

A generated table row or an embedded data URI may legitimately exceed the limit. Raise the threshold or omit the entry for generated documents.

## Disable and verify

Remove this command entry from `PostToolUse` in the same settings file. Run `python -B test_hook.py` from this folder to check the hook independently.
