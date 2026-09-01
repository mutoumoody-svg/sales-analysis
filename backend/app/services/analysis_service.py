"""
Analysis Service - 高级分析模型.

包含:
1. ABC分析  - SKU按收入/利润贡献分类 (A/B/C)
2. GMROI    - 库存投资毛利率回报
3. 销售预测 - 基于历史趋势的线性回归预测
4. 现金流预测 - 基于销售预测+成本+费用推算
"""

from datetime import date, timedelta
from typing import Optional
from collections import defaultdict

from sqlalchemy.orm import Session
from sqlalchemy import func, desc, asc

from app.models import SalesSummary, Product, Inventory, Expense, Store
from app.models.order import Order


class AnalysisService:
    """高级分析服务."""

    # ============================================================
    # 1. ABC 分析
    # ============================================================

    def get_abc_analysis(
        self,
        db: Session,
        period: Optional[str] = None,
        brand: Optional[str] = None,
        metric: str = "revenue",
    ) -> dict:
        """ABC分类分析.

        Args:
            period: 期间 YYYY-MM，None则取全部
            brand: 品牌过滤
            metric: 分类依据 - 'revenue' 或 'profit'

        Returns:
            {
                summary: { a_count, b_count, c_count, a_revenue, b_revenue, c_revenue, ... },
                items: [{ sku, product_name, brand, revenue, profit, qty, cum_pct, grade }]
            }
        """
        query = (
            db.query(
                Product.sku,
                Product.product_name,
                Product.brand,
                Product.category,
                func.sum(SalesSummary.net_qty).label("qty"),
                func.sum(SalesSummary.net_amount).label("revenue"),
                func.sum(SalesSummary.net_profit).label("profit"),
                func.sum(SalesSummary.net_cost).label("cost"),
            )
            .join(Product, SalesSummary.product_id == Product.id)
        )

        if period:
            query = query.filter(SalesSummary.period == period)
        if brand and brand != "ALL":
            query = query.filter(Product.brand == brand)

        query = query.group_by(
            Product.sku, Product.product_name, Product.brand, Product.category
        )

        sort_col = func.sum(SalesSummary.net_amount) if metric == "revenue" else func.sum(SalesSummary.net_profit)
        query = query.order_by(desc(sort_col))

        rows = query.all()

        if not rows:
            return {
                "summary": {
                    "total_skus": 0, "a_count": 0, "b_count": 0, "c_count": 0,
                    "total_revenue": 0, "total_profit": 0,
                    "a_revenue": 0, "b_revenue": 0, "c_revenue": 0,
                    "a_profit": 0, "b_profit": 0, "c_profit": 0,
                },
                "items": [],
            }

        total_value = sum(float(r.revenue or 0) if metric == "revenue" else float(r.profit or 0) for r in rows)
        if total_value == 0:
            total_value = 1  # 避免除0

        items = []
        cum_value = 0.0
        total_revenue = sum(float(r.revenue or 0) for r in rows)
        total_profit = sum(float(r.profit or 0) for r in rows)

        a_revenue, b_revenue, c_revenue = 0.0, 0.0, 0.0
        a_profit, b_profit, c_profit = 0.0, 0.0, 0.0
        a_count, b_count, c_count = 0, 0, 0

        for r in rows:
            value = float(r.revenue or 0) if metric == "revenue" else float(r.profit or 0)
            cum_value += value
            cum_pct = (cum_value / total_value) * 100

            if cum_pct <= 70:
                grade = "A"
                a_count += 1
                a_revenue += float(r.revenue or 0)
                a_profit += float(r.profit or 0)
            elif cum_pct <= 90:
                grade = "B"
                b_count += 1
                b_revenue += float(r.revenue or 0)
                b_profit += float(r.profit or 0)
            else:
                grade = "C"
                c_count += 1
                c_revenue += float(r.revenue or 0)
                c_profit += float(r.profit or 0)

            items.append({
                "sku": r.sku,
                "product_name": r.product_name,
                "brand": r.brand,
                "category": r.category,
                "qty": int(r.qty or 0),
                "revenue": round(float(r.revenue or 0), 2),
                "profit": round(float(r.profit or 0), 2),
                "cost": round(float(r.cost or 0), 2),
                "margin_pct": round((float(r.profit or 0) / float(r.revenue or 1)) * 100, 1) if r.revenue else 0,
                "cum_pct": round(cum_pct, 1),
                "grade": grade,
            })

        return {
            "summary": {
                "total_skus": len(rows),
                "a_count": a_count, "b_count": b_count, "c_count": c_count,
                "total_revenue": round(total_revenue, 2),
                "total_profit": round(total_profit, 2),
                "a_revenue": round(a_revenue, 2),
                "b_revenue": round(b_revenue, 2),
                "c_revenue": round(c_revenue, 2),
                "a_profit": round(a_profit, 2),
                "b_profit": round(b_profit, 2),
                "c_profit": round(c_profit, 2),
                "a_revenue_pct": round((a_revenue / total_revenue) * 100, 1) if total_revenue else 0,
                "b_revenue_pct": round((b_revenue / total_revenue) * 100, 1) if total_revenue else 0,
                "c_revenue_pct": round((c_revenue / total_revenue) * 100, 1) if total_revenue else 0,
            },
            "items": items,
        }

    # ============================================================
    # 2. GMROI 分析
    # ============================================================

    def get_gmroi_analysis(
        self,
        db: Session,
        period: Optional[str] = None,
        brand: Optional[str] = None,
    ) -> dict:
        """GMROI - 库存投资毛利率回报.

        GMROI = 毛利 / 平均库存成本

        对于有库存数据的SKU:
        - 库存成本 = available_qty * unit_cost
        - GMROI = net_profit / 库存成本 * 100
        - 周转率 = net_qty / available_qty (近似的库存周转)
        """
        # 1. 获取库存数据（只取最新日期，避免历史快照叠加）
        latest_inv_date = db.query(func.max(Inventory.date)).scalar()
        inv_query = (
            db.query(
                Inventory.product_id,
                func.sum(Inventory.available_qty).label("available_qty"),
                func.sum(Inventory.reserved_qty).label("reserved_qty"),
                func.sum(Inventory.inbound_qty).label("inbound_qty"),
            )
            .filter(Inventory.date == latest_inv_date)
            .group_by(Inventory.product_id)
        )
        inv_map = {r.product_id: r for r in inv_query.all()}

        # 2. 获取销售汇总
        sales_query = (
            db.query(
                Product.id,
                Product.sku,
                Product.product_name,
                Product.brand,
                Product.category,
                Product.unit_cost,
                func.sum(SalesSummary.net_qty).label("qty"),
                func.sum(SalesSummary.net_amount).label("revenue"),
                func.sum(SalesSummary.net_cost).label("cost"),
                func.sum(SalesSummary.net_profit).label("profit"),
            )
            .join(Product, SalesSummary.product_id == Product.id)
        )

        if period:
            sales_query = sales_query.filter(SalesSummary.period == period)
        if brand and brand != "ALL":
            sales_query = sales_query.filter(Product.brand == brand)

        sales_query = sales_query.group_by(
            Product.id, Product.sku, Product.product_name, Product.brand, Product.category, Product.unit_cost
        )

        rows = sales_query.all()

        items = []
        total_inv_cost = 0.0
        total_profit = 0.0
        positive_gmroi_count = 0
        negative_gmroi_count = 0
        no_inventory_count = 0

        for r in rows:
            inv = inv_map.get(r.id)
            available = int(inv.available_qty) if inv else 0
            reserved = int(inv.reserved_qty) if inv else 0
            inbound = int(inv.inbound_qty) if inv else 0
            effective = available + inbound - reserved

            unit_cost = float(r.unit_cost or 0)
            inv_cost = available * unit_cost

            profit = float(r.profit or 0)
            revenue = float(r.revenue or 0)
            qty = int(r.qty or 0)

            gmroi = (profit / inv_cost * 100) if inv_cost > 0 else None
            turnover = (qty / available) if available > 0 else None

            if inv_cost == 0:
                no_inventory_count += 1
            elif gmroi is not None and gmroi > 0:
                positive_gmroi_count += 1
            elif gmroi is not None:
                negative_gmroi_count += 1

            total_inv_cost += inv_cost
            total_profit += profit

            items.append({
                "sku": r.sku,
                "product_name": r.product_name,
                "brand": r.brand,
                "category": r.category,
                "available_qty": available,
                "effective_qty": effective,
                "unit_cost": round(unit_cost, 4),
                "inv_cost": round(inv_cost, 2),
                "qty": qty,
                "revenue": round(revenue, 2),
                "profit": round(profit, 2),
                "gmroi": round(gmroi, 1) if gmroi is not None else None,
                "turnover": round(turnover, 2) if turnover is not None else None,
                "margin_pct": round((profit / revenue) * 100, 1) if revenue > 0 else 0,
                "status": "no_inventory" if inv_cost == 0 else ("good" if gmroi and gmroi > 0 else "poor"),
            })

        # 按GMROI降序 (None放最后)
        items.sort(key=lambda x: x["gmroi"] if x["gmroi"] is not None else -99999, reverse=True)

        overall_gmroi = (total_profit / total_inv_cost * 100) if total_inv_cost > 0 else 0

        return {
            "summary": {
                "total_skus": len(rows),
                "total_inv_cost": round(total_inv_cost, 2),
                "total_profit": round(total_profit, 2),
                "overall_gmroi": round(overall_gmroi, 1),
                "positive_gmroi_count": positive_gmroi_count,
                "negative_gmroi_count": negative_gmroi_count,
                "no_inventory_count": no_inventory_count,
            },
            "items": items,
        }

    # ============================================================
    # 3. 销售预测
    # ============================================================

    def get_sales_forecast(
        self,
        db: Session,
        brand: Optional[str] = None,
        forecast_months: int = 3,
    ) -> dict:
        """销售预测 - 基于历史月度数据的线性回归.

        使用最小二乘法拟合趋势线，预测未来N个月。
        同时计算环比增长率作为参考。
        """
        # 获取所有月份的汇总数据
        query = (
            db.query(
                SalesSummary.period,
                func.sum(SalesSummary.net_amount).label("revenue"),
                func.sum(SalesSummary.net_profit).label("profit"),
                func.sum(SalesSummary.net_qty).label("qty"),
                func.sum(SalesSummary.net_cost).label("cost"),
                func.sum(SalesSummary.ship_qty).label("ship_qty"),
                func.sum(SalesSummary.return_qty).label("return_qty"),
            )
        )

        if brand and brand != "ALL":
            query = query.join(Product, SalesSummary.product_id == Product.id).filter(Product.brand == brand)

        query = query.group_by(SalesSummary.period).order_by(SalesSummary.period)

        rows = query.all()

        if not rows:
            return {
                "history": [],
                "forecast": [],
                "trend": {"slope": 0, "intercept": 0, "avg_growth_rate": 0, "r_squared": 0},
                "summary": {"next_month_revenue": 0, "confidence": "low"},
            }

        # 历史数据
        history = []
        for r in rows:
            history.append({
                "period": r.period,
                "revenue": round(float(r.revenue or 0), 2),
                "profit": round(float(r.profit or 0), 2),
                "qty": int(r.qty or 0),
                "cost": round(float(r.cost or 0), 2),
                "ship_qty": int(r.ship_qty or 0),
                "return_qty": int(r.return_qty or 0),
            })

        n = len(history)
        if n < 2:
            # 只有1个月数据，用环比增长率为0
            forecast = []
            last_rev = history[-1]["revenue"] if history else 0
            last_profit = history[-1]["profit"] if history else 0
            last_cost = history[-1]["cost"] if history else 0
            for i in range(1, forecast_months + 1):
                # 解析最后一个月
                yr, mo = history[-1]["period"].split("-")
                next_mo = int(mo) + i
                next_yr = int(yr)
                while next_mo > 12:
                    next_mo -= 12
                    next_yr += 1
                forecast.append({
                    "period": f"{next_yr}-{next_mo:02d}",
                    "revenue": round(last_rev, 2),
                    "profit": round(last_profit, 2),
                    "cost": round(last_cost, 2),
                    "is_forecast": True,
                })
            return {
                "history": history,
                "forecast": forecast,
                "trend": {"slope": 0, "intercept": last_rev, "avg_growth_rate": 0, "r_squared": 0},
                "summary": {
                    "next_month_revenue": round(last_rev, 2),
                    "confidence": "low",
                    "data_points": n,
                },
            }

        # 线性回归 (最小二乘法)
        x = list(range(n))
        y_rev = [h["revenue"] for h in history]
        y_profit = [h["profit"] for h in history]
        y_cost = [h["cost"] for h in history]

        x_mean = sum(x) / n
        y_mean = sum(y_rev) / n

        numerator = sum((xi - x_mean) * (yi - y_mean) for xi, yi in zip(x, y_rev))
        denominator = sum((xi - x_mean) ** 2 for xi in x)

        slope = numerator / denominator if denominator != 0 else 0
        intercept = y_mean - slope * x_mean

        # R² 计算
        y_pred = [slope * xi + intercept for xi in x]
        ss_res = sum((yi - yp) ** 2 for yi, yp in zip(y_rev, y_pred))
        ss_tot = sum((yi - y_mean) ** 2 for yi in y_rev)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0

        # 利润趋势
        y_profit_mean = sum(y_profit) / n
        num_p = sum((xi - x_mean) * (yi - y_profit_mean) for xi, yi in zip(x, y_profit))
        slope_profit = num_p / denominator if denominator != 0 else 0
        intercept_profit = y_profit_mean - slope_profit * x_mean

        # 成本趋势
        y_cost_mean = sum(y_cost) / n
        num_c = sum((xi - x_mean) * (yi - y_cost_mean) for xi, yi in zip(x, y_cost))
        slope_cost = num_c / denominator if denominator != 0 else 0
        intercept_cost = y_cost_mean - slope_cost * x_mean

        # 平均环比增长率
        growth_rates = []
        for i in range(1, n):
            if y_rev[i - 1] > 0:
                growth_rates.append((y_rev[i] - y_rev[i - 1]) / y_rev[i - 1] * 100)
        avg_growth = sum(growth_rates) / len(growth_rates) if growth_rates else 0

        # 预测未来N个月
        forecast = []
        last_period = history[-1]["period"]
        yr, mo = last_period.split("-")
        yr, mo = int(yr), int(mo)

        for i in range(1, forecast_months + 1):
            next_x = n - 1 + i
            next_mo = mo + i
            next_yr = yr
            while next_mo > 12:
                next_mo -= 12
                next_yr += 1

            pred_rev = max(0, slope * next_x + intercept)
            pred_profit = max(0, slope_profit * next_x + intercept_profit)
            pred_cost = max(0, slope_cost * next_x + intercept_cost)

            forecast.append({
                "period": f"{next_yr}-{next_mo:02d}",
                "revenue": round(pred_rev, 2),
                "profit": round(pred_profit, 2),
                "cost": round(pred_cost, 2),
                "is_forecast": True,
            })

        # 置信度评估
        if r_squared >= 0.7 and n >= 4:
            confidence = "high"
        elif r_squared >= 0.4 and n >= 3:
            confidence = "medium"
        else:
            confidence = "low"

        return {
            "history": history,
            "forecast": forecast,
            "trend": {
                "slope": round(slope, 2),
                "intercept": round(intercept, 2),
                "slope_profit": round(slope_profit, 2),
                "intercept_profit": round(intercept_profit, 2),
                "avg_growth_rate": round(avg_growth, 1),
                "r_squared": round(r_squared, 4),
            },
            "summary": {
                "next_month_revenue": forecast[0]["revenue"] if forecast else 0,
                "next_month_profit": forecast[0]["profit"] if forecast else 0,
                "confidence": confidence,
                "data_points": n,
                "trend_direction": "up" if slope > 0 else ("down" if slope < 0 else "flat"),
            },
        }

    # ============================================================
    # 4. 现金流预测
    # ============================================================

    def get_cashflow_forecast(
        self,
        db: Session,
        brand: Optional[str] = None,
        forecast_months: int = 3,
    ) -> dict:
        """现金流预测.

        基于销售预测推算:
        - 现金流入 = 预测销售额
        - 现金流出 = 预测成本 + 费用(广告/物流/平台/固定等)
        - 净现金流 = 流入 - 流出
        - 累计现金流
        """
        # 获取销售预测
        sales_forecast = self.get_sales_forecast(db, brand, forecast_months)

        # 获取历史费用数据
        expense_query = (
            db.query(
                Expense.expense_type,
                func.sum(Expense.amount).label("amount"),
            )
            .group_by(Expense.expense_type)
        )
        expense_rows = expense_query.all()

        # 如果有费用数据，按月平均
        expense_data = {}
        total_monthly_expense = 0.0
        if expense_rows:
            # 获取费用覆盖的月数
            expense_count = db.query(func.count(func.distinct(func.to_char(Expense.date, 'YYYY-MM')))).scalar() or 1
            expense_count = max(1, expense_count)

            for r in expense_rows:
                monthly_avg = float(r.amount or 0) / expense_count
                expense_data[r.expense_type] = round(monthly_avg, 2)
                total_monthly_expense += monthly_avg

        # 历史现金流
        history = []
        for h in sales_forecast["history"]:
            revenue = h["revenue"]
            cost = h["cost"]
            profit = h["profit"]
            # 估算费用 (如果有历史费用数据，按比例分摊；否则用利润的15%估算运营费用)
            estimated_expense = total_monthly_expense if total_monthly_expense > 0 else abs(profit) * 0.15
            net_cashflow = revenue - cost - estimated_expense
            history.append({
                "period": h["period"],
                "inflow": round(revenue, 2),
                "outflow_cost": round(cost, 2),
                "outflow_expense": round(estimated_expense, 2),
                "net_cashflow": round(net_cashflow, 2),
                "cumulative": 0,  # 后面计算
            })

        # 预测现金流
        forecast = []
        for f in sales_forecast["forecast"]:
            revenue = f["revenue"]
            cost = f["cost"]
            estimated_expense = total_monthly_expense if total_monthly_expense > 0 else abs(f["profit"]) * 0.15
            net_cashflow = revenue - cost - estimated_expense
            forecast.append({
                "period": f["period"],
                "inflow": round(revenue, 2),
                "outflow_cost": round(cost, 2),
                "outflow_expense": round(estimated_expense, 2),
                "net_cashflow": round(net_cashflow, 2),
                "cumulative": 0,
                "is_forecast": True,
            })

        # 计算累计现金流
        all_periods = history + forecast
        cum = 0.0
        for p in all_periods:
            cum += p["net_cashflow"]
            p["cumulative"] = round(cum, 2)

        # 费用明细
        expense_breakdown = []
        for etype, amount in expense_data.items():
            expense_breakdown.append({
                "type": etype,
                "monthly_avg": amount,
                "pct": round((amount / total_monthly_expense) * 100, 1) if total_monthly_expense > 0 else 0,
            })
        expense_breakdown.sort(key=lambda x: x["monthly_avg"], reverse=True)

        return {
            "history": history,
            "forecast": forecast,
            "expense_breakdown": expense_breakdown,
            "has_expense_data": len(expense_rows) > 0,
            "summary": {
                "next_month_inflow": forecast[0]["inflow"] if forecast else 0,
                "next_month_outflow": (forecast[0]["outflow_cost"] + forecast[0]["outflow_expense"]) if forecast else 0,
                "next_month_net": forecast[0]["net_cashflow"] if forecast else 0,
                "avg_monthly_expense": round(total_monthly_expense, 2),
                "forecast_total_net": round(sum(f["net_cashflow"] for f in forecast), 2),
                "trend": sales_forecast["summary"]["trend_direction"],
            },
        }

    # ============================================================
    # 5. 经营区间分析 (最优运营区间)
    # ============================================================

    def get_optimal_interval(
        self,
        db: Session,
        brand: Optional[str] = None,
    ) -> dict:
        """最优经营区间分析.

        分析不同折扣率区间的利润表现，找出最优折扣区间。
        """
        query = (
            db.query(
                Product.sku,
                Product.product_name,
                Product.brand,
                SalesSummary.period,
                SalesSummary.ship_amount,
                SalesSummary.net_amount,
                SalesSummary.net_profit,
                SalesSummary.net_qty,
                SalesSummary.net_cost,
            )
            .join(Product, SalesSummary.product_id == Product.id)
        )

        if brand and brand != "ALL":
            query = query.filter(Product.brand == brand)

        rows = query.all()

        if not rows:
            return {"intervals": [], "optimal": None}

        # 计算每个SKU-月份的折扣率
        records = []
        for r in rows:
            if r.ship_amount and r.ship_amount > 0 and r.net_qty and r.net_qty > 0:
                discount_rate = (1 - float(r.net_amount or 0) / float(r.ship_amount)) * 100
                records.append({
                    "discount_rate": discount_rate,
                    "revenue": float(r.net_amount or 0),
                    "profit": float(r.net_profit or 0),
                    "cost": float(r.net_cost or 0),
                    "qty": int(r.net_qty or 0),
                })

        if not records:
            return {"intervals": [], "optimal": None}

        # 按5%区间分组
        intervals_map = defaultdict(lambda: {"count": 0, "revenue": 0, "profit": 0, "cost": 0, "qty": 0})
        for rec in records:
            bucket = int(rec["discount_rate"] // 5) * 5
            bucket = max(0, min(50, bucket))
            key = f"{bucket}-{bucket+5}%"
            intervals_map[key]["count"] += 1
            intervals_map[key]["revenue"] += rec["revenue"]
            intervals_map[key]["profit"] += rec["profit"]
            intervals_map[key]["cost"] += rec["cost"]
            intervals_map[key]["qty"] += rec["qty"]

        intervals = []
        for key, val in sorted(intervals_map.items()):
            margin = (val["profit"] / val["revenue"] * 100) if val["revenue"] > 0 else 0
            intervals.append({
                "discount_range": key,
                "sku_count": val["count"],
                "revenue": round(val["revenue"], 2),
                "profit": round(val["profit"], 2),
                "cost": round(val["cost"], 2),
                "qty": val["qty"],
                "margin_pct": round(margin, 1),
                "avg_profit_per_sku": round(val["profit"] / val["count"], 2) if val["count"] > 0 else 0,
            })

        # 找最优区间 (按总利润排序)
        optimal = max(intervals, key=lambda x: x["profit"]) if intervals else None

        return {
            "intervals": intervals,
            "optimal": optimal,
        }


analysis_service = AnalysisService()
