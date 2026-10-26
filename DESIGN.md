# Design notes: Publicity & Marketing Management System

## Module map (`src/pubmarket/`)

- `analytics.py`
- `calendar.py`
- `report.py`
- `store.py`

## Test strategy

- Tests use only `unittest` (run with `python -m unittest` or `pytest`). Each test asserts a behaviour, with known-answer cases where a closed form exists, not just that code runs.
- Paths that need external services (LLM API, webcam) are isolated behind small interfaces and are NOT covered by the unit tests; each README says so.

## Failure modes considered

- Integrity lives in the schema (CHECK constraints, foreign keys, UNIQUE per campaign/channel/day) so bad data cannot get in via any code path.
- Metric import is an upsert, so re-running an import for a day is idempotent.
- Ratios return None on a zero denominator rather than inf/0, so 'no data' is never displayed as 'great' or 'terrible'.

## Known gaps

- Reallocation uses last-touch ROAS and assumes channels are independent and returns are linear; real channels saturate and interact.
- No ad-platform API connectors; metrics are recorded through `Store.record_metrics`.
- Single-user SQLite; no auth or UI.
