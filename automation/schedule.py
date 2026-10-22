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
    return next_available_publish_slot(config, now, [])


def next_available_publish_slot(config: dict, now: datetime, occupied: list[str]) -> datetime:
    channel_zone = ZoneInfo(config["channel"]["timezone"])
    schedule = config["schedule"]
    hour, minute = (int(part) for part in schedule["publish_time"].split(":"))
    videos_per_day = max(1, min(5, int(schedule.get("videos_per_day", 1))))
    first_minutes = hour * 60 + minute
    daily_minutes = sorted({(first_minutes + round(1440 * index / videos_per_day)) % 1440 for index in range(videos_per_day)})
    allowed = {WEEKDAYS[name.lower()] for name in schedule["publish_days"]}
    local_now = now.astimezone(channel_zone)

    occupied_values = {
        datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(channel_zone).replace(second=0, microsecond=0)
        for value in occupied if value
    }
    for offset in range(0, 64):
        day = local_now.date() + timedelta(days=offset)
        if datetime.combine(day, time(0, 0), tzinfo=channel_zone).weekday() not in allowed:
            continue
        for minute_of_day in daily_minutes:
            candidate = datetime.combine(day, time(minute_of_day // 60, minute_of_day % 60), tzinfo=channel_zone)
            if candidate > local_now + timedelta(minutes=15) and candidate not in occupied_values:
                return candidate
    raise RuntimeError("No unoccupied publish slot found in the next sixty-four days")


def requested_or_next(config: dict, value: str | None, now: datetime, occupied: list[str] | None = None) -> datetime:
    if not value:
        return next_available_publish_slot(config, now, occupied or [])
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        raise ValueError("requested_publish_at must contain an explicit timezone")
    if parsed <= now:
        raise ValueError("requested_publish_at must be in the future")
    return parsed
