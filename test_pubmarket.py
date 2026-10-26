import sqlite3, unittest
from datetime import date
from pubmarket import Store, budget_pacing, channel_kpis, find_conflicts, find_gaps, recommend_reallocation
from pubmarket.report import markdown_report

D = lambda d: date(2026, 11, d)


def seeded():
    s = Store()
    cid = s.create_campaign("Diwali Push", 10_000, D(1), D(30), {"search": 6000, "social": 4000})
    for day in range(1, 11):
        s.record_metrics(cid, "search", D(day), 10_000, 500, 25, 200.0, 800.0)   # ROAS 4.0
        s.record_metrics(cid, "social", D(day), 50_000, 500, 5, 200.0, 200.0)    # ROAS 1.0
    return s, cid


class StoreTests(unittest.TestCase):
    def test_channel_budgets_cannot_exceed_campaign(self):
        with self.assertRaises(ValueError):
            Store().create_campaign("x", 100, D(1), D(2), {"a": 80, "b": 40})

    def test_db_constraints(self):
        s, cid = seeded()
        with self.assertRaises(sqlite3.IntegrityError):
            s.record_metrics(cid, "search", D(20), impressions=10, clicks=99, conversions=0, spend=0, revenue=0)
        with self.assertRaises(sqlite3.IntegrityError):
            s.create_campaign("bad dates", 1, D(5), D(1))

    def test_metrics_upsert_is_idempotent(self):
        s, cid = seeded()
        s.record_metrics(cid, "search", D(1), 10_000, 500, 25, 200.0, 800.0)
        n = s.db.execute("SELECT COUNT(*) FROM metrics WHERE channel='search' AND day=?", (D(1).isoformat(),)).fetchone()[0]
        self.assertEqual(n, 1)


class AnalyticsTests(unittest.TestCase):
    def test_kpis(self):
        s, cid = seeded()
        k = channel_kpis(s, cid)["search"]
        self.assertAlmostEqual(k["ctr"], 0.05)
        self.assertAlmostEqual(k["cpa"], 8.0)
        self.assertAlmostEqual(k["roas"], 4.0)
        self.assertAlmostEqual(k["roi"], 3.0)

    def test_zero_denominators_give_none(self):
        s = Store(); cid = s.create_campaign("c", 100, D(1), D(5))
        s.record_metrics(cid, "x", D(1), 0, 0, 0, 0.0, 0.0)
        k = channel_kpis(s, cid)["x"]
        self.assertTrue(all(k[m] is None for m in ("ctr", "cpc", "cpa", "roas")))

    def test_pacing(self):
        s, cid = seeded()                                   # 4000 of 10000 spent
        self.assertEqual(budget_pacing(s, cid, D(10))["status"], "overspending")   # 40% spend / 33% time = 1.2
        self.assertEqual(budget_pacing(s, cid, D(12))["status"], "on_track")       # 40% / 40% = 1.0
        self.assertEqual(budget_pacing(s, cid, D(25))["status"], "underspending")  # 40% / 83% = 0.48

    def test_reallocation_moves_money_toward_higher_roas(self):
        s, cid = seeded()
        moves = recommend_reallocation(channel_kpis(s, cid))
        self.assertLess(moves["social"], 0)
        self.assertGreater(moves["search"], 0)
        self.assertAlmostEqual(sum(moves.values()), 0, places=1)

    def test_reallocation_refuses_on_thin_data(self):
        self.assertEqual(recommend_reallocation({"a": {"roas": 9, "spend": 5}, "b": {"roas": 1, "spend": 5}}), {})


class CalendarTests(unittest.TestCase):
    def test_conflicts_ignore_cancelled(self):
        s = Store(); cid = s.create_campaign("c", 100, D(1), D(30))
        ids = [s.schedule_content(cid, "ig", D(3), f"post{i}") for i in range(3)]
        self.assertEqual(len(find_conflicts(s, cid)), 1)
        s.set_status(ids[0], "cancelled")
        self.assertEqual(find_conflicts(s, cid), [])

    def test_gaps(self):
        s = Store(); cid = s.create_campaign("c", 100, D(1), D(30))
        for d in (2, 3, 25):
            s.schedule_content(cid, "ig", D(d), "p")
        self.assertEqual(find_gaps(s, cid, "ig", 7), [(D(4), D(24))])


class ReportTests(unittest.TestCase):
    def test_report_renders(self):
        s, cid = seeded()
        md = markdown_report(s, cid, D(10))
        self.assertIn("| search |", md)
        self.assertIn("Suggested reallocation", md)


if __name__ == "__main__":
    unittest.main()
