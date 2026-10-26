from __future__ import annotations
from datetime import date
from .analytics import budget_pacing, channel_kpis, recommend_reallocation
from .store import Store


def _fmt(v, kind="num"):
    if v is None: return "n/a"
    return f"{v:.1%}" if kind == "pct" else f"{v:,.2f}"


def markdown_report(store: Store, campaign_id: int, today: date) -> str:
    c, kp, pace = store.campaign(campaign_id), channel_kpis(store, campaign_id), budget_pacing(store, campaign_id, today)
    lines = [f"# Campaign report: {c['name']}", "",
             f"Budget {pace['budget']:,.0f} | spent {pace['spent']:,.0f} | time elapsed {pace['time_pct']:.0%} | spend {pace['spend_pct']:.0%} | **{pace['status']}**", "",
             "| Channel | Spend | CTR | CPA | ROAS |", "|---|---|---|---|---|"]
    for ch, k in sorted(kp.items()):
        lines.append(f"| {ch} | {_fmt(k['spend'])} | {_fmt(k['ctr'], 'pct')} | {_fmt(k['cpa'])} | {_fmt(k['roas'])} |")
    moves = recommend_reallocation(kp)
    lines += ["", "## Suggested reallocation" if moves else "## Suggested reallocation: none (insufficient data)"]
    lines += [f"- {ch}: {d:+,.0f}" for ch, d in sorted(moves.items())]
    return "\n".join(lines)
