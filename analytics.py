from __future__ import annotations
from datetime import date
from .store import Store


def _div(a: float, b: float) -> float | None:
    return a / b if b else None


def channel_kpis(store: Store, campaign_id: int) -> dict[str, dict[str, float | None]]:
    rows = store.db.execute(
        """SELECT channel, SUM(impressions) i, SUM(clicks) c, SUM(conversions) v, SUM(spend) s, SUM(revenue) r
           FROM metrics WHERE campaign_id=? GROUP BY channel""", (campaign_id,)).fetchall()
    out = {}
    for r in rows:
        out[r["channel"]] = {
            "impressions": r["i"], "spend": r["s"], "revenue": r["r"],
            "ctr": _div(r["c"], r["i"]), "cpc": _div(r["s"], r["c"]), "cpa": _div(r["s"], r["v"]),
            "roas": _div(r["r"], r["s"]), "roi": _div(r["r"] - r["s"], r["s"]),
        }
    return out


def budget_pacing(store: Store, campaign_id: int, today: date) -> dict:
    """Compare % of budget spent with % of flight time elapsed. >1.15 overspending, <0.85 underspending."""
    c = store.campaign(campaign_id)
    start, end = date.fromisoformat(c["start_date"]), date.fromisoformat(c["end_date"])
    total_days = (end - start).days + 1
    elapsed = min(max((today - start).days + 1, 0), total_days)
    spent = store.db.execute("SELECT COALESCE(SUM(spend),0) FROM metrics WHERE campaign_id=?", (campaign_id,)).fetchone()[0]
    time_pct, spend_pct = elapsed / total_days, (spent / c["budget"] if c["budget"] else 0)
    ratio = spend_pct / time_pct if time_pct else 0.0
    status = "on_track" if 0.85 <= ratio <= 1.15 else ("overspending" if ratio > 1.15 else "underspending")
    return {"spent": spent, "budget": c["budget"], "time_pct": round(time_pct, 3), "spend_pct": round(spend_pct, 3),
            "pace_ratio": round(ratio, 2), "status": status}


def recommend_reallocation(kpis: dict, max_shift_pct: float = 0.2, min_spend_to_judge: float = 100.0) -> dict[str, float]:
    """Suggest budget deltas per channel: shift up to max_shift_pct of total spend from low-ROAS to high-ROAS channels.

    Only channels with at least `min_spend_to_judge` of spend are judged: below that, ROAS is noise.
    Returns {channel: delta}; deltas sum to ~0. Empty dict if there is nothing defensible to recommend.
    """
    judged = {c: k for c, k in kpis.items() if k["roas"] is not None and k["spend"] >= min_spend_to_judge}
    if len(judged) < 2:
        return {}
    total = sum(k["spend"] for k in judged.values())
    mean_roas = sum(k["roas"] * k["spend"] for k in judged.values()) / total   # spend-weighted
    pool = max_shift_pct * total
    losers = {c: max(0.0, mean_roas - k["roas"]) * k["spend"] for c, k in judged.items()}
    winners = {c: max(0.0, k["roas"] - mean_roas) * k["spend"] for c, k in judged.items()}
    lsum, wsum = sum(losers.values()), sum(winners.values())
    if not lsum or not wsum:
        return {}
    deltas = {}
    for c, k in judged.items():
        if losers[c]:
            deltas[c] = -min(pool * losers[c] / lsum, k["spend"] * 0.5)   # never cut a channel by more than half
    cut = -sum(deltas.values())
    for c in judged:
        if winners[c]:
            deltas[c] = cut * winners[c] / wsum
    return {c: round(v, 2) for c, v in deltas.items()}
