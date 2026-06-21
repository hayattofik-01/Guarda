"""Interval helpers for Guarda's automated, always-on checks."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from app.models import Frequency

_INTERVALS: dict[Frequency, timedelta] = {
    Frequency.hourly: timedelta(hours=1),
    Frequency.daily: timedelta(days=1),
    Frequency.weekly: timedelta(weeks=1),
    Frequency.monthly: timedelta(days=30),
}


def interval_for(frequency: Frequency) -> timedelta:
    return _INTERVALS.get(frequency, timedelta(weeks=1))


def next_run(frequency: Frequency, *, after: datetime | None = None) -> datetime:
    """Return the next due time for the given cadence."""
    base = after or datetime.now(UTC)
    if base.tzinfo is None:
        base = base.replace(tzinfo=UTC)
    return base + interval_for(frequency)
