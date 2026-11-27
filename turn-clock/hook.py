"""Supply one timestamp to the host for each supported event."""
from datetime import datetime, timedelta, timezone
import json
import os
import re
import sys
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError


WEEKDAYS = {
    "en": ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"),
    "fr": ("lun", "mar", "mer", "jeu", "ven", "sam", "dim"),
    "es": ("lun", "mar", "mi\u00e9", "jue", "vie", "s\u00e1b", "dom"),
}
EVENTS = ("UserPromptSubmit", "PostToolBatch")


def configured_zone(value):
    if value == "local":
        return None  # astimezone(None) applies system rules at the requested instant.
    if value == "UTC":
        return timezone.utc
    offset = re.fullmatch(r"([+-])([01][0-9]|2[0-3]):([0-5][0-9])", value)
    if offset:
        sign, hours, minutes = offset.groups()
        delta = timedelta(hours=int(hours), minutes=int(minutes))
        return timezone(delta if sign == "+" else -delta)
    try:
        return ZoneInfo(value)
    except (ValueError, ZoneInfoNotFoundError) as exc:
        raise ValueError("TURN_CLOCK_ZONE needs local, UTC, +HH:MM, -HH:MM, or an available IANA zone") from exc


def context(event, instant, zone, weekdays):
    local = instant.astimezone(zone)
    utc = instant.astimezone(timezone.utc)
    stamp = f"{local.isoformat(timespec='seconds')} ({weekdays[local.weekday()]})"
    utc_stamp = utc.strftime("%Y-%m-%dT%H:%M:%SZ")
    if event == "PostToolBatch":
        return f"Tool batch ended: {stamp} | UTC: {utc_stamp}"
    upcoming = []
    for offset in range(1, 8):
        day = local.date() + timedelta(days=offset)
        upcoming.append(f"{day.isoformat()} {weekdays[day.weekday()]}")
    return f"Now: {stamp} | UTC: {utc_stamp} | Next 7 days: {', '.join(upcoming)}"


def main():
    try:
        payload = json.loads(sys.stdin.buffer.read().decode("utf-8-sig"))
    except (ValueError, RecursionError):
        return 0
    if not isinstance(payload, dict) or payload.get("hook_event_name") not in EVENTS:
        return 0
    event = payload["hook_event_name"]
    language = os.getenv("TURN_CLOCK_LANG", "en")
    if language not in WEEKDAYS:
        print("TURN_CLOCK_LANG must be en, fr, or es", file=sys.stderr)
        return 1
    try:
        zone = configured_zone(os.getenv("TURN_CLOCK_ZONE", "local"))
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    line = context(event, datetime.now(timezone.utc), zone, WEEKDAYS[language])
    print(json.dumps({"hookSpecificOutput": {"hookEventName": event, "additionalContext": line}}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
