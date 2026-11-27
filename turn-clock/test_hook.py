"""Check calendar boundaries and the two command registrations."""
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest
from zoneinfo import TZPATH, ZoneInfo, reset_tzpath

import hook


HERE = Path(__file__).resolve().parent


def call(raw, cwd, **settings):
    env = os.environ.copy()
    for key in ("TURN_CLOCK_ZONE", "TURN_CLOCK_LANG"):
        env.pop(key, None)
    env.update(settings)
    return subprocess.run([sys.executable, "-I", "-B", str(HERE / "hook.py")],
                          input=raw, capture_output=True, cwd=cwd, env=env,
                          timeout=10)


class ClockTests(unittest.TestCase):
    def test_year_boundary_and_seven_local_dates(self):
        instant = datetime(2030, 12, 31, 21, 30, tzinfo=timezone.utc)
        line = hook.context("UserPromptSubmit", instant, hook.configured_zone("+05:30"), hook.WEEKDAYS["en"])
        self.assertEqual(line, "Now: 2031-01-01T03:00:00+05:30 (Wed) | UTC: 2030-12-31T21:30:00Z | "
                         "Next 7 days: 2031-01-02 Thu, 2031-01-03 Fri, 2031-01-04 Sat, "
                         "2031-01-05 Sun, 2031-01-06 Mon, 2031-01-07 Tue, 2031-01-08 Wed")

    def test_leap_day_and_negative_offset(self):
        instant = datetime(2032, 2, 29, 1, 30, tzinfo=timezone.utc)
        line = hook.context("UserPromptSubmit", instant, hook.configured_zone("-04:00"), hook.WEEKDAYS["es"])
        self.assertIn("2032-02-28T21:30:00-04:00", line)
        self.assertIn("Next 7 days: 2032-02-29 dom, 2032-03-01 lun", line)

    def test_system_zone(self):
        instant = datetime(2031, 1, 1, tzinfo=timezone.utc)
        self.assertIsNone(hook.configured_zone("local"))
        expected = instant.astimezone().isoformat(timespec="seconds")
        self.assertIn(expected, hook.context("PostToolBatch", instant, None, hook.WEEKDAYS["en"]))

    def test_iana_daylight_change_without_system_zone_database(self):
        # A minimal TZif with a forward jump from UTC to UTC+1.
        transition = datetime(2030, 3, 31, 1, tzinfo=timezone.utc)
        header = b"TZif" + bytes(16) + struct.pack(">6l", 0, 0, 0, 1, 2, 8)
        records = struct.pack(">lB", int(transition.timestamp()), 1)
        records += struct.pack(">lBB", 0, 0, 0) + struct.pack(">lBB", 3600, 1, 4)
        with tempfile.TemporaryDirectory() as tmp:
            Path(tmp, "Example").write_bytes(header + records + b"STD\0DST\0")
            try:
                reset_tzpath([str(Path(tmp).resolve())])
                zone = hook.configured_zone("Example")
                before = transition - timedelta(seconds=1)
                self.assertIn("00:59:59+00:00", hook.context("PostToolBatch", before, zone, hook.WEEKDAYS["en"]))
                self.assertIn("02:00:00+01:00", hook.context("PostToolBatch", transition, zone, hook.WEEKDAYS["en"]))
            finally:
                ZoneInfo.clear_cache(only_keys=["Example"])
                reset_tzpath(TZPATH)

    def test_entry_points(self):
        with tempfile.TemporaryDirectory(prefix="clock checks ") as tmp:
            for event in hook.EVENTS:
                raw = json.dumps({"hook_event_name": event}).encode("utf-8-sig") + b"\r\n"
                proc = call(raw, tmp, TURN_CLOCK_ZONE="UTC", TURN_CLOCK_LANG="fr")
                self.assertEqual((proc.returncode, proc.stderr), (0, b""))
                out = json.loads(proc.stdout)["hookSpecificOutput"]
                self.assertEqual(out["hookEventName"], event)
                self.assertEqual(len(out["additionalContext"].splitlines()), 1)
                self.assertEqual("Next 7 days:" in out["additionalContext"], event == "UserPromptSubmit")
                self.assertIn("UTC:", out["additionalContext"])
                self.assertNotIn("permissionDecision", out)

    def test_bad_configuration(self):
        raw = b'{"hook_event_name":"UserPromptSubmit"}'
        for setting in ({"TURN_CLOCK_LANG": "unknown"}, {"TURN_CLOCK_ZONE": "+24:00"},
                        {"TURN_CLOCK_ZONE": "Invalid/Nowhere"}):
            with self.subTest(setting=setting):
                proc = call(raw, HERE, **setting)
                self.assertEqual((proc.returncode, proc.stdout), (1, b""))
                self.assertIn(next(iter(setting)).encode(), proc.stderr)

    def test_ignore_unrelated_or_invalid_input(self):
        for raw in (b"{", b"null", b"\xff", b"{}", b'{"hook_event_name":"Stop"}'):
            proc = call(raw, HERE)
            self.assertEqual((proc.returncode, proc.stdout, proc.stderr), (0, b"", b""))


if __name__ == "__main__":
    unittest.main()
