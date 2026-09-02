# Legacy sales engine provenance

These modules were migrated from `mutoumoody-svg/sales-agent` commit
`7888ea2` as the starting point for the unified monthly-close workflow.

- `wangdiantong.py`: confirmed store scope, WDT file parsing and returns.
- `analyzer.py`: SKU cost matching, gross-profit and analysis tables.
- `reporter.py`: formatted Excel exports.

Keep changes covered by reconciliation tests against confirmed historical
monthly results before deploying them.
