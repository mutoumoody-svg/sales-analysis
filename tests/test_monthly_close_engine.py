import tempfile
from pathlib import Path

import pandas as pd

from app.services.monthly_close_engine import analyze_wdt_pair


def test_two_file_monthly_close_uses_detail_revenue_and_summary_returns():
    detail = pd.DataFrame([{
        "订单编号": "202609020000001",
        "店铺": "天猫-巴恩天然旗舰店",
        "货品编号": "BNMGO100",
        "货品名称": "MGO100+",
        "货品数量": 2,
        "货品成交总价": 200,
        "应收金额": 200,
        "发货时间": "2026-08-10 12:00:00",
        "赠品方式": "",
    }])
    summary = pd.DataFrame([{
        "店铺": "天猫-巴恩天然旗舰店",
        "货品编号": "BNMGO100",
        "货品名称": "MGO100+",
        "总销量": 2,
        "实际销售量": 1,
        "发货总金额": 200,
        "实际销售额": 100,
    }])
    with tempfile.TemporaryDirectory() as directory:
        detail_path = Path(directory) / "detail.xlsx"
        summary_path = Path(directory) / "summary.xlsx"
        detail.to_excel(detail_path, index=False)
        summary.to_excel(summary_path, index=False)
        result = analyze_wdt_pair(detail_path, summary_path, "2026-08")

    store = result["巴恩天然天猫旗舰店_天猫"]
    assert store["summary"]["总销售额(商家收入)"] == 100
    assert store["summary"]["合计总成本"] == 40
    assert store["summary"]["总毛利润"] == 60

