from __future__ import annotations

import unittest
from datetime import datetime, timezone

from automation.schedule import next_publish_slot, requested_or_next


CONFIG = {
    "channel": {"timezone": "Asia/Kolkata"},
    "schedule": {
        "publish_days": ["tuesday", "thursday", "saturday"],
        "publish_time": "19:30",
    },
}


class ScheduleTests(unittest.TestCase):
    def test_next_slot_uses_channel_timezone(self):
        # Monday 18:00 IST -> Tuesday 19:30 IST.
        now = datetime(2026, 10, 19, 12, 30, tzinfo=timezone.utc)
        result = next_publish_slot(CONFIG, now)
        self.assertEqual(result.isoformat(), "2026-10-20T19:30:00+05:30")

    def test_same_day_slot_requires_fifteen_minute_buffer(self):
        # Tuesday 19:20 IST is too late; choose Thursday.
        now = datetime(2026, 10, 20, 13, 50, tzinfo=timezone.utc)
        result = next_publish_slot(CONFIG, now)
        self.assertEqual(result.isoformat(), "2026-10-22T19:30:00+05:30")

    def test_requested_time_requires_timezone(self):
        with self.assertRaisesRegex(ValueError, "explicit timezone"):
            requested_or_next(CONFIG, "2026-10-24T19:30:00", datetime(2026, 10, 20, tzinfo=timezone.utc))

    def test_requested_time_must_be_future(self):
        with self.assertRaisesRegex(ValueError, "future"):
            requested_or_next(CONFIG, "2020-01-01T00:00:00Z", datetime(2026, 10, 20, tzinfo=timezone.utc))


if __name__ == "__main__":
    unittest.main()
