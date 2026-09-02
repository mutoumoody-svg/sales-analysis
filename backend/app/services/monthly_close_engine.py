"""Canonical two-file monthly-close calculation based on the sales-agent rules."""

from pathlib import Path

import pandas as pd

from app.legacy_sales_engine import analyzer, wangdiantong as wdt


def _metric(summary_df: pd.DataFrame | None, key: str, default: float = 0) -> float:
    if summary_df is None or "指标" not in summary_df.columns:
        return default
    value = summary_df.set_index("指标")["数值"].to_dict().get(key, default)
    if isinstance(value, str):
        try:
            return float(value.strip().rstrip("%")) / (100 if value.strip().endswith("%") else 1)
        except ValueError:
            return default
    return float(value) if pd.notna(value) else default


def _summary(sheets: dict[str, pd.DataFrame]) -> dict:
    frame = sheets.get("毛利汇总")
    keys = ["总销售额(商家收入)", "合计总成本", "总毛利润", "推广费用合计", "合计税费", "总订单数", "总销量(正品)"]
    result = {key: _metric(frame, key) for key in keys}
    revenue = result["总销售额(商家收入)"]
    gross = result["总毛利润"]
    ads = result["推广费用合计"]
    result["整体毛利率"] = gross / revenue if revenue else 0
    result["营销后净利润"] = gross - ads
    result["净利润率"] = (gross - ads) / revenue if revenue else 0
    return result


def apply_returns(orders: pd.DataFrame, products: pd.DataFrame, returns: pd.DataFrame, period_date: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    adjustment_products: list[dict] = []
    adjustment_orders: list[dict] = []
    date_value = pd.to_datetime(period_date).date()
    for _, row in returns.iterrows():
        sku = str(row["SKU编码"])
        qty = int(row["退货量"])
        amount = float(row["退货总金额"])
        order_id = f"RET-{sku}"
        adjustment_products.append({"主订单号": order_id, "日期": date_value, "下单时间": "", "SKU编码": sku, "商品名称": str(row.get("货品名称", "")), "是否赠品": "正品", "销量": -qty, "标价": 0.0, "商家收入": -amount, "订单状态": "退货"})
        adjustment_orders.append({"主订单号": order_id, "日期": date_value, "下单时间": "", "订单状态": "退货", "商家收入": -amount, "商品数量": -qty, "省": "", "市": ""})
    if adjustment_products:
        products = pd.concat([products, pd.DataFrame(adjustment_products)], ignore_index=True)
        orders = pd.concat([orders, pd.DataFrame(adjustment_orders)], ignore_index=True)
    return orders, products


def analyze_wdt_pair(detail_file: str | Path, summary_file: str | Path | None, period: str) -> dict:
    """Analyze the two WDT files using exactly the confirmed-store sales rules.

    The detail file is the primary revenue source. The summary file contributes
    return deductions only, matching the existing sales application.
    """
    if len(period) != 7 or period[4] != "-":
        raise ValueError("period must use YYYY-MM")
    period_date = f"{period}-15"
    detail = wdt.load_file(str(detail_file))
    returns_source = wdt.load_file(str(summary_file)) if summary_file else None
    stores = wdt.list_recognized_stores(detail)
    if not stores:
        raise ValueError("销售出库明细中没有识别到已确认的电商店铺")

    results: dict[str, dict] = {}
    for raw_name, store_name, platform in stores:
        orders, products = wdt.parse_store(wdt.extract_store_df(detail, raw_name), period_date)
        if returns_source is not None:
            for return_raw, mapped, return_platform in wdt.list_recognized_stores(returns_source):
                if mapped == store_name and return_platform == platform:
                    returns = wdt.extract_returns(returns_source, return_raw)
                    orders, products = apply_returns(orders, products, returns, period_date)
                    break
        sheets = analyzer.build_all(orders, products, None, None, platform=platform, store=store_name)
        results[f"{store_name}_{platform}"] = {
            "name": store_name,
            "platform": platform,
            "source": "wdt_detail",
            "summary": _summary(sheets),
            "sheets": {key: frame.to_dict("records") for key, frame in sheets.items()},
        }
    return results

