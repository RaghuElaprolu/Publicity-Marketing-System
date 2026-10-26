# Publicity & Marketing Management System

Plans campaigns and content calendars, tracks spend and results by channel, and suggests budget moves.

![tests](https://img.shields.io/badge/tests-unittest-blue) ![python](https://img.shields.io/badge/python-3.10%2B-blue)

## Architecture

```
SQLite (campaigns, channel_budgets, content_items, metrics)
   -> analytics: CTR, CPC, CPA, ROAS, ROI | budget pacing (spend% vs time%)
   -> reallocation: shift <=20% of spend from below-average to above-average ROAS channels
   -> calendar: per-day channel caps, silent gaps -> markdown report
```

## Quick start

```bash
# no required dependencies (standard library only)
PYTHONPATH=src python -m pubmarket.demo
PYTHONPATH=src python -m unittest discover -s tests -v
```

## Key design decisions

- Integrity lives in the schema (CHECK constraints, foreign keys, UNIQUE per campaign/channel/day) so bad data cannot get in via any code path.
- Metric import is an upsert, so re-running an import for a day is idempotent.
- Ratios return None on a zero denominator rather than inf/0, so 'no data' is never displayed as 'great' or 'terrible'.
- Reallocation refuses to judge channels with <100 spend (ROAS is noise there), caps cuts at 50% per channel, and is zero-sum.

## Limitations (read before using)

- Reallocation uses last-touch ROAS and assumes channels are independent and returns are linear; real channels saturate and interact.
- No ad-platform API connectors; metrics are recorded through `Store.record_metrics`.
- Single-user SQLite; no auth or UI.

## Next steps

- Add connectors (Google Ads / Meta) behind the same `record_metrics` interface.
- Model diminishing returns per channel before recommending shifts.
- A small FastAPI + dashboard front end.

See [docs/DESIGN.md](docs/DESIGN.md) for the module map and test strategy.
