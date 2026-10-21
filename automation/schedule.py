from __future__ import annotations

from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo


WEEKDAYS = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}


def next_publish_slot(config: dict, now: datetime) -> datetime:
    channel_zone = ZoneInfo(config["channel"]["timezone"])
    schedule = config["schedule"]
    hour, minute = (int(part) for part in schedule["publish_time"].split(":"))
    allowed = {WEEKDAYS[name.lower()] for name in schedule["publish_days"]}
    local_now = now.astimezone(channel_zone)

    for offset in range(0, 8):
        day = local_now.date() + timedelta(days=offset)
        candidate = datetime.combine(day, time(hour, minute), tzinfo=channel_zone)
        if candidate.weekday() in allowed and candidate > local_now + timedelta(minutes=15):
            return candidate
    raise RuntimeError("No publish slot found in the next seven days")


def requested_or_next(config: dict, value: str | None, now: datetime) -> datetime:
    if not value:
        return next_publish_slot(config, now)
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("requested_publish_at must contain an explicit timezone")
    if parsed <= now:
        raise ValueError("requested_publish_at must be in the future")
    return parsed
