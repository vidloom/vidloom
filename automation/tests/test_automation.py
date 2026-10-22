from __future__ import annotations

import unittest
from datetime import datetime, timezone

from automation.schedule import next_publish_slot, requested_or_next
from automation.production import select_item
from automation.autopilot import autopilot_mode, recoverable_idea


CONFIG = {
    "channel": {"timezone": "Asia/Kolkata"},
    "schedule": {
        "publish_days": ["tuesday", "thursday", "saturday"],
        "publish_time": "19:30",
        "videos_per_day": 1,
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

    def test_explicit_held_item_cannot_run(self):
        queue = {"items": [{"id": "held-one", "status": "held"}]}
        with self.assertRaisesRegex(RuntimeError, "expected one of"):
            select_item(queue, "held-one")

    def test_multiple_daily_slots_are_spread_evenly(self):
        config = {
            "channel": {"timezone": "Asia/Kolkata"},
            "schedule": {"publish_days": ["tuesday"], "publish_time": "20:00", "videos_per_day": 2},
        }
        # Tuesday 07:00 IST -> first chronological slot is 08:00, then 20:00.
        now = datetime(2026, 10, 20, 1, 30, tzinfo=timezone.utc)
        first = next_publish_slot(config, now)
        self.assertEqual(first.isoformat(), "2026-10-20T08:00:00+05:30")


class AutopilotTests(unittest.TestCase):
    def test_buffer_counts_active_work_before_commissioning(self):
        config = {"automation": {"creator_enabled": True, "finished_buffer_target": 3}}
        queue = {"items": [{"status": "ready"}, {"status": "scheduled"}]}
        ideas = {"items": [{"id": "new", "status": "scripting"}]}
        state = autopilot_mode(config, queue, ideas)
        self.assertEqual(state["gap"], 0)
        self.assertEqual(state["mode"], "creating")

    def test_blocked_idea_is_retried_only_within_limit(self):
        config = {"automation": {"automatic_retries": True, "maximum_job_retries": 3}}
        ideas = {"items": [{"id": "retry", "origin": "autopilot", "status": "blocked", "attempts": 2}]}
        self.assertEqual(recoverable_idea(config, ideas)["id"], "retry")
        ideas["items"][0]["attempts"] = 3
        self.assertIsNone(recoverable_idea(config, ideas))


if __name__ == "__main__":
    unittest.main()
