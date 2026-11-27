# Turn clock

On each user prompt the hook adds a single line with the local timestamp, numeric UTC offset, local weekday, UTC timestamp, and the next seven local calendar dates with weekdays. After each completed tool batch it adds a fresh timestamp and weekday without repeating the calendar. Both lines are returned in `hookSpecificOutput.additionalContext`. The host must support the event you register. You can register the prompt event alone.

## Registration

Copy this folder to a stable location. Replace `HOOKS_HOME` with its full parent directory. Merge the entries into your host's `hooks` settings. Each registration calls the same script; the host supplies the event name in the JSON payload.

```json
{
  "hooks": {
    "UserPromptSubmit": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python -I -B \"HOOKS_HOME/turn-clock/hook.py\""
          }
        ]
      }
    ],
    "PostToolBatch": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "python -I -B \"HOOKS_HOME/turn-clock/hook.py\""
          }
        ]
      }
    ]
  }
}
```

## Configuration

| Environment variable | Default | Values |
|---|---|---|
| `TURN_CLOCK_ZONE` | `local` | System local time at the instant of the event. Choose `UTC`, a fixed offset such as `+05:30`, or an IANA name such as `Europe/Paris` if the interpreter has the zone database. |
| `TURN_CLOCK_LANG` | `en` | Short weekday names in English (`en`), French (`fr`), or Spanish (`es`). Dates stay in year-month-day order. |

Set these in the host's environment. Fixed offsets work on both platforms without a timezone database. For a region that observes daylight saving, choose system local time or an available named zone. An unknown zone or language produces a configuration error on stderr and no clock line. Unrelated events and malformed payloads produce no output.

## A rule to use alongside the clock

Use a date command for weekday and interval calculations. For example, `python -c "from datetime import date; print(date(2031, 1, 3).isoweekday())"` prints `5` for Friday. The preview includes weekends. Business-day calculations need the applicable holiday calendar.

## Prior work

| Project | Stars | Latest default-branch commit (UTC date) | Behavior in the inspected revision |
|---|---:|---|---|
| [pvc-timestamp-hook](https://raw.githubusercontent.com/pro-vibe-coding/pvc-timestamp-hook/419acefec39c7f6186aee3e54cbdf88d611c286d/SKILL.md) | 4 | 2026-09-22 | Adds the current date, weekday, and time to each user prompt. |
| [chronos](https://raw.githubusercontent.com/OthmanAdi/chronos/eb5438d2448a10ffd9c835d733bfebc0ba3278b8/lib/hooks.js) | 3 | 2026-09-04 | Reports session timing and can add elapsed-time context when the user returns. |
| [temporal-awareness](https://raw.githubusercontent.com/hodgesmr/temporal-awareness/36c0a04941ea19c49868ca3deb4b7482168a0bb1/skills/temporal-awareness/SKILL.md) | 10 | 2026-01-22 | Directs the assistant to use a date command for calendar questions. |

Repository counts were checked on 2026-11-27. In these revisions we did not find the full combination of a seven-day preview, a timestamp after every tool batch, and a companion rule for date arithmetic.

Run `python -B test_hook.py` in this folder to check both events, date boundaries, and configuration errors.
