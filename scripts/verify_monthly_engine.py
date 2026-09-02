"""Compare the migrated two-file engine with a confirmed sales result JSON."""

import argparse
import json

from app.services.monthly_close_engine import analyze_wdt_pair


METRICS = ["总销售额(商家收入)", "合计总成本", "总毛利润"]


def totals(payload: dict) -> dict[str, float]:
    return {metric: round(sum(float((row.get("summary") or {}).get(metric, 0) or 0) for row in payload.values()), 2) for metric in METRICS}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--detail", required=True)
    parser.add_argument("--summary", required=True)
    parser.add_argument("--expected", required=True)
    parser.add_argument("--period", required=True)
    args = parser.parse_args()
    actual = totals(analyze_wdt_pair(args.detail, args.summary, args.period))
    with open(args.expected, encoding="utf-8") as handle:
        expected = totals(json.load(handle))
    print(json.dumps({"period": args.period, "actual": actual, "expected": expected,
                      "difference": {key: round(actual[key] - expected[key], 2) for key in METRICS}}, ensure_ascii=False))
    return 0 if actual[METRICS[0]] == expected[METRICS[0]] else 1


if __name__ == "__main__":
    raise SystemExit(main())
