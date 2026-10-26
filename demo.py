from datetime import date
from .report import markdown_report
from .store import Store


def main() -> None:
    s = Store()
    D = lambda d: date(2026, 11, d)
    cid = s.create_campaign("Diwali Push", 10_000, D(1), D(30), {"search": 6000, "social": 4000})
    for day in range(1, 13):
        s.record_metrics(cid, "search", D(day), 10_000, 500, 25, 200.0, 800.0)
        s.record_metrics(cid, "social", D(day), 50_000, 500, 5, 200.0, 200.0)
    print("SEEDED DEMO DATA\n")
    print(markdown_report(s, cid, D(12)))


if __name__ == "__main__":
    main()
