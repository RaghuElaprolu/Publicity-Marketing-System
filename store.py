from __future__ import annotations
import sqlite3
from datetime import date

SCHEMA = """
CREATE TABLE IF NOT EXISTS campaigns(
  id INTEGER PRIMARY KEY, name TEXT NOT NULL UNIQUE, budget REAL NOT NULL CHECK(budget >= 0),
  start_date TEXT NOT NULL, end_date TEXT NOT NULL, CHECK(end_date >= start_date));
CREATE TABLE IF NOT EXISTS channel_budgets(
  campaign_id INTEGER NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
  channel TEXT NOT NULL, budget REAL NOT NULL CHECK(budget >= 0), PRIMARY KEY(campaign_id, channel));
CREATE TABLE IF NOT EXISTS content_items(
  id INTEGER PRIMARY KEY, campaign_id INTEGER NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
  channel TEXT NOT NULL, publish_date TEXT NOT NULL, title TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'planned' CHECK(status IN ('planned','approved','published','cancelled')));
CREATE TABLE IF NOT EXISTS metrics(
  id INTEGER PRIMARY KEY, campaign_id INTEGER NOT NULL REFERENCES campaigns(id) ON DELETE CASCADE,
  channel TEXT NOT NULL, day TEXT NOT NULL, impressions INTEGER NOT NULL DEFAULT 0,
  clicks INTEGER NOT NULL DEFAULT 0, conversions INTEGER NOT NULL DEFAULT 0,
  spend REAL NOT NULL DEFAULT 0, revenue REAL NOT NULL DEFAULT 0,
  UNIQUE(campaign_id, channel, day), CHECK(clicks <= impressions));
"""


class Store:
    def __init__(self, path: str = ":memory:") -> None:
        self.db = sqlite3.connect(path)
        self.db.row_factory = sqlite3.Row
        self.db.execute("PRAGMA foreign_keys = ON")
        self.db.executescript(SCHEMA)

    def create_campaign(self, name: str, budget: float, start: date, end: date, channel_budgets: dict[str, float] | None = None) -> int:
        channel_budgets = channel_budgets or {}
        if sum(channel_budgets.values()) > budget + 1e-9:
            raise ValueError("channel budgets exceed campaign budget")
        with self.db:
            cur = self.db.execute("INSERT INTO campaigns(name,budget,start_date,end_date) VALUES(?,?,?,?)",
                                  (name, budget, start.isoformat(), end.isoformat()))
            cid = cur.lastrowid
            self.db.executemany("INSERT INTO channel_budgets VALUES(?,?,?)", [(cid, c, b) for c, b in channel_budgets.items()])
        return cid

    def schedule_content(self, campaign_id: int, channel: str, when: date, title: str) -> int:
        with self.db:
            return self.db.execute("INSERT INTO content_items(campaign_id,channel,publish_date,title) VALUES(?,?,?,?)",
                                   (campaign_id, channel, when.isoformat(), title)).lastrowid

    def set_status(self, item_id: int, status: str) -> None:
        with self.db:
            self.db.execute("UPDATE content_items SET status=? WHERE id=?", (status, item_id))

    def record_metrics(self, campaign_id: int, channel: str, day: date, impressions: int, clicks: int,
                       conversions: int, spend: float, revenue: float) -> None:
        with self.db:  # upsert so re-importing a day is idempotent
            self.db.execute(
                """INSERT INTO metrics(campaign_id,channel,day,impressions,clicks,conversions,spend,revenue)
                   VALUES(?,?,?,?,?,?,?,?)
                   ON CONFLICT(campaign_id,channel,day) DO UPDATE SET impressions=excluded.impressions,
                   clicks=excluded.clicks, conversions=excluded.conversions, spend=excluded.spend, revenue=excluded.revenue""",
                (campaign_id, channel, day.isoformat(), impressions, clicks, conversions, spend, revenue))

    def campaign(self, campaign_id: int) -> sqlite3.Row:
        return self.db.execute("SELECT * FROM campaigns WHERE id=?", (campaign_id,)).fetchone()
