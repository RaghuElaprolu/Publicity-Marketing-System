from __future__ import annotations
from collections import defaultdict
from datetime import date, timedelta
from .store import Store


def find_conflicts(store: Store, campaign_id: int | None = None, max_per_channel_per_day: int = 2) -> list[dict]:
    """Days where a channel has more live items than the cap (cancelled items ignored)."""
    q = """SELECT channel, publish_date, COUNT(*) n, GROUP_CONCAT(title, ' | ') titles FROM content_items
           WHERE status != 'cancelled' {where} GROUP BY channel, publish_date HAVING n > ?"""
    args: list = []
    where = ""
    if campaign_id is not None:
        where, args = "AND campaign_id = ?", [campaign_id]
    rows = store.db.execute(q.format(where=where), args + [max_per_channel_per_day]).fetchall()
    return [dict(r) for r in rows]


def find_gaps(store: Store, campaign_id: int, channel: str, max_gap_days: int = 7) -> list[tuple[date, date]]:
    """Silent stretches longer than max_gap_days inside the campaign flight for a channel."""
    c = store.campaign(campaign_id)
    start, end = date.fromisoformat(c["start_date"]), date.fromisoformat(c["end_date"])
    days = sorted({date.fromisoformat(r[0]) for r in store.db.execute(
        "SELECT publish_date FROM content_items WHERE campaign_id=? AND channel=? AND status!='cancelled'", (campaign_id, channel))})
    marks = [start - timedelta(days=1)] + [d for d in days if start <= d <= end] + [end + timedelta(days=1)]
    return [(a + timedelta(days=1), b - timedelta(days=1)) for a, b in zip(marks, marks[1:]) if (b - a).days - 1 > max_gap_days]
