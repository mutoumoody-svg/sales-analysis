"""
AI Agent Service - 6 agents for business analysis.

Each agent queries real data, applies domain-specific business rules,
generates structured insights and saves recommendations to ai_recommendations.

Agents:
1. Sales Agent      - sales trends, channel performance, SKU rankings, return analysis
2. Inventory Agent  - stock health, stockout risk, stale inventory, capital occupation
3. Procurement Agent - reorder suggestions, purchase priority, quantity recommendations
4. Finance Agent    - gross margin, net profit, loss-making SKUs, capital efficiency
5. Operation Agent  - pricing optimization, promo opportunities, low margin alerts
6. CEO Agent        - aggregates all agents, generates 3 questions + 3 actions
"""

import uuid
from typing import Optional, Dict, List, Any
from datetime import date, timedelta
from collections import defaultdict

from sqlalchemy.orm import Session
from sqlalchemy import func, desc, and_, case, literal

from app.models import (
    SalesSummary, Product, Store, Inventory,
    AIRecommendation, Order, OrderItem,
)
from app.utils.period import resolve_period, get_latest_period, get_available_periods, period_to_date_range
from app.services.reorder_service import calculate_reorder, PROCUREMENT_DAYS, SAFETY_FACTOR_FAST

# 滞销判定：库存 > 50件 且 月销量 < 5件
STALE_STOCK_THRESHOLD = 50
STALE_SALES_THRESHOLD = 5


class BaseAgent:
    """Base class for all business analysis agents."""

    agent_type = "Base Agent"

    def __init__(self, db: Session):
        self.db = db

    def analyze(self, period: str, brand: Optional[str] = None) -> Dict[str, Any]:
        """Run analysis and return structured results."""
        raise NotImplementedError

    def _save_recommendations(self, recommendations: List[Dict[str, Any]]):
        """Save recommendations to ai_recommendations table."""
        for rec in recommendations:
            entry = AIRecommendation(
                agent_type=self.agent_type,
                recommendation=rec.get("recommendation", ""),
                priority=rec.get("priority", "Medium"),
                target_type=rec.get("target_type"),
                target_id=uuid.UUID(rec["target_id"]) if rec.get("target_id") else None,
            )
            self.db.add(entry)
        self.db.commit()

    def _clear_old(self):
        """Clear old recommendations from this agent type."""
        self.db.query(AIRecommendation).filter(
            AIRecommendation.agent_type == self.agent_type
        ).delete()
        self.db.commit()

    def _apply_brand_filter(self, query, brand: Optional[str]):
        """Apply brand filter to a query that joins Product."""
        if brand:
            return query.join(Product, SalesSummary.product_id == Product.id).filter(Product.brand == brand)
        return query


# ============================================================
# 1. Sales Agent
# ============================================================
class SalesAgent(BaseAgent):
    """销售分析Agent: 趋势、渠道表现、SKU排名、退货分析."""

    agent_type = "Sales Agent"

    def analyze(self, period: str, brand: Optional[str] = None) -> Dict[str, Any]:
        self._clear_old()
        recommendations = []
        insights = {}

        # --- 1. 当月核心指标 ---
        q = (
            self.db.query(
                func.sum(SalesSummary.net_amount).label("revenue"),
                func.sum(SalesSummary.net_cost).label("cost"),
                func.sum(SalesSummary.net_profit).label("profit"),
                func.sum(SalesSummary.ship_qty).label("ship_qty"),
                func.sum(SalesSummary.return_qty).label("return_qty"),
                func.sum(SalesSummary.ship_amount).label("ship_amount"),
                func.sum(SalesSummary.return_amount).label("return_amount"),
                func.sum(SalesSummary.net_qty).label("net_qty"),
                func.sum(SalesSummary.commission_cost).label("commission"),
            )
            .filter(SalesSummary.period == period)
        )
        q = self._apply_brand_filter(q, brand)
        s = q.first()

        revenue = float(s.revenue) if s.revenue else 0
        profit = float(s.profit) if s.profit else 0
        cost = float(s.cost) if s.cost else 0
        ship_qty = int(s.ship_qty) if s.ship_qty else 0
        return_qty = int(s.return_qty) if s.return_qty else 0
        ship_amount = float(s.ship_amount) if s.ship_amount else 0
        return_amount = float(s.return_amount) if s.return_amount else 0
        net_qty = int(s.net_qty) if s.net_qty else 0
        commission = float(s.commission) if s.commission else 0

        gross_margin = (profit / revenue * 100) if revenue > 0 else 0
        return_rate = (return_amount / ship_amount * 100) if ship_amount > 0 else 0

        insights["summary"] = {
            "revenue": round(revenue, 2),
            "profit": round(profit, 2),
            "cost": round(cost, 2),
            "gross_margin": round(gross_margin, 2),
            "ship_qty": ship_qty,
            "return_qty": return_qty,
            "net_qty": net_qty,
            "return_rate": round(return_rate, 2),
            "commission": round(commission, 2),
        }

        # --- 2. 月环比 (MoM) ---
        periods_data = get_available_periods(self.db)
        sorted_periods = sorted([p["period"] for p in periods_data], reverse=True)
        current_idx = None
        for i, p in enumerate(sorted_periods):
            if p == period:
                current_idx = i
                break

        mom_change = None
        if current_idx is not None and current_idx + 1 < len(sorted_periods):
            prev_period = sorted_periods[current_idx + 1]
            prev_q = (
                self.db.query(
                    func.sum(SalesSummary.net_amount).label("revenue"),
                    func.sum(SalesSummary.net_profit).label("profit"),
                )
                .filter(SalesSummary.period == prev_period)
            )
            prev_q = self._apply_brand_filter(prev_q, brand)
            prev = prev_q.first()
            prev_revenue = float(prev.revenue) if prev.revenue else 0
            prev_profit = float(prev.profit) if prev.profit else 0

            if prev_revenue > 0:
                mom_change = {
                    "prev_period": prev_period,
                    "prev_revenue": round(prev_revenue, 2),
                    "prev_profit": round(prev_profit, 2),
                    "revenue_change_pct": round((revenue - prev_revenue) / prev_revenue * 100, 1),
                    "profit_change_pct": round((profit - prev_profit) / abs(prev_profit) * 100, 1) if prev_profit != 0 else None,
                }
                insights["mom"] = mom_change

                if mom_change["revenue_change_pct"] < -10:
                    recommendations.append({
                        "recommendation": f"销售额环比下降 {abs(mom_change['revenue_change_pct'])}%（{prev_period}: ¥{prev_revenue:,.0f} → {period}: ¥{revenue:,.0f}），需排查下滑原因：是否季节性、竞品冲击、流量减少",
                        "priority": "High",
                        "target_type": "overall",
                    })
                elif mom_change["revenue_change_pct"] > 20:
                    recommendations.append({
                        "recommendation": f"销售额环比增长 {mom_change['revenue_change_pct']}%（¥{prev_revenue:,.0f} → ¥{revenue:,.0f}），建议分析增长驱动因素并固化成功经验",
                        "priority": "Medium",
                        "target_type": "overall",
                    })

        # --- 3. 店铺/渠道表现 ---
        store_q = (
            self.db.query(
                Store.store_name,
                Store.platform,
                func.sum(SalesSummary.net_amount).label("revenue"),
                func.sum(SalesSummary.net_profit).label("profit"),
                func.sum(SalesSummary.ship_qty).label("ship_qty"),
                func.sum(SalesSummary.return_amount).label("return_amount"),
                func.sum(SalesSummary.ship_amount).label("ship_amount"),
            )
            .join(Store, SalesSummary.store_id == Store.id)
            .filter(SalesSummary.period == period)
            .group_by(Store.store_name, Store.platform)
            .order_by(desc(func.sum(SalesSummary.net_amount)))
        )
        store_q = self._apply_brand_filter(store_q, brand) if brand else store_q
        store_results = store_q.all()

        stores_data = []
        for r in store_results:
            s_rev = float(r.revenue) if r.revenue else 0
            s_profit = float(r.profit) if r.profit else 0
            s_ret = float(r.return_amount) if r.return_amount else 0
            s_ship = float(r.ship_amount) if r.ship_amount else 0
            s_rr = (s_ret / s_ship * 100) if s_ship > 0 else 0
            stores_data.append({
                "store_name": r.store_name,
                "platform": r.platform,
                "revenue": round(s_rev, 2),
                "profit": round(s_profit, 2),
                "ship_qty": int(r.ship_qty) if r.ship_qty else 0,
                "return_rate": round(s_rr, 2),
            })

        insights["stores"] = stores_data

        if len(stores_data) >= 2:
            best = stores_data[0]
            worst = stores_data[-1]
            if best["revenue"] > 0:
                recommendations.append({
                    "recommendation": f"店铺「{best['store_name']}」销售额最高（¥{best['revenue']:,.0f}），占比 {best['revenue']/revenue*100:.1f}%，是核心收入来源",
                    "priority": "Medium",
                    "target_type": "store",
                })
            if worst["revenue"] < best["revenue"] * 0.1 and worst["revenue"] > 0:
                recommendations.append({
                    "recommendation": f"店铺「{worst['store_name']}」销售额仅 ¥{worst['revenue']:,.0f}，不足最优店铺的10%，建议评估是否继续投入或调整运营策略",
                    "priority": "Medium",
                    "target_type": "store",
                })

        # --- 4. SKU排名 ---
        sku_q = (
            self.db.query(
                Product.sku,
                Product.product_name,
                Product.brand,
                func.sum(SalesSummary.net_qty).label("qty"),
                func.sum(SalesSummary.net_amount).label("revenue"),
                func.sum(SalesSummary.net_profit).label("profit"),
            )
            .join(Product, SalesSummary.product_id == Product.id)
            .filter(SalesSummary.period == period)
            .group_by(Product.sku, Product.product_name, Product.brand)
            .order_by(desc(func.sum(SalesSummary.net_amount)))
        )
        if brand:
            sku_q = sku_q.filter(Product.brand == brand)
        sku_results = sku_q.all()

        top_skus = []
        bottom_skus = []
        for r in sku_results[:10]:
            top_skus.append({
                "sku": r.sku,
                "name": r.product_name,
                "brand": r.brand,
                "qty": int(r.qty) if r.qty else 0,
                "revenue": round(float(r.revenue), 2) if r.revenue else 0,
                "profit": round(float(r.profit), 2) if r.profit else 0,
            })
        for r in sku_results[-5:] if len(sku_results) > 5 else []:
            if r.revenue and float(r.revenue) > 0:
                bottom_skus.append({
                    "sku": r.sku,
                    "name": r.product_name,
                    "brand": r.brand,
                    "qty": int(r.qty) if r.qty else 0,
                    "revenue": round(float(r.revenue), 2),
                    "profit": round(float(r.profit), 2) if r.profit else 0,
                })

        insights["top_skus"] = top_skus
        insights["bottom_skus"] = bottom_skus

        # SKU集中度
        if sku_results and revenue > 0:
            top3_revenue = sum(float(r.revenue) if r.revenue else 0 for r in sku_results[:3])
            concentration = top3_revenue / revenue * 100
            insights["sku_concentration"] = round(concentration, 1)
            if concentration > 60:
                recommendations.append({
                    "recommendation": f"TOP3 SKU贡献了 {concentration:.1f}% 的销售额，收入集中度过高，建议培育更多爆品分散风险",
                    "priority": "High",
                    "target_type": "overall",
                })

        # --- 5. 退货分析 ---
        if return_rate > 15:
            recommendations.append({
                "recommendation": f"退货率 {return_rate:.1f}% 严重偏高（退货金额 ¥{return_amount:,.0f}），需立即排查产品质量、描述一致性和物流问题",
                "priority": "High",
                "target_type": "overall",
            })
        elif return_rate > 8:
            recommendations.append({
                "recommendation": f"退货率 {return_rate:.1f}% 偏高，建议分析高退货SKU并优化产品详情页",
                "priority": "Medium",
                "target_type": "overall",
            })

        # 高退货SKU
        high_return_q = (
            self.db.query(
                Product.sku,
                Product.product_name,
                func.sum(SalesSummary.ship_amount).label("ship_amt"),
                func.sum(SalesSummary.return_amount).label("ret_amt"),
            )
            .join(Product, SalesSummary.product_id == Product.id)
            .filter(SalesSummary.period == period)
            .group_by(Product.sku, Product.product_name)
            .having(func.sum(SalesSummary.ship_amount) > 1000)
        )
        if brand:
            high_return_q = high_return_q.filter(Product.brand == brand)
        high_return_results = high_return_q.all()

        high_return_skus = []
        for r in high_return_results:
            ship_amt = float(r.ship_amt) if r.ship_amt else 0
            ret_amt = float(r.ret_amt) if r.ret_amt else 0
            if ship_amt > 0:
                rr = ret_amt / ship_amt * 100
                if rr > 20:
                    high_return_skus.append({
                        "sku": r.sku,
                        "name": r.product_name,
                        "return_rate": round(rr, 1),
                        "return_amount": round(ret_amt, 2),
                    })
        high_return_skus.sort(key=lambda x: x["return_rate"], reverse=True)
        insights["high_return_skus"] = high_return_skus[:5]

        if high_return_skus:
            worst = high_return_skus[0]
            recommendations.append({
                "recommendation": f"SKU「{worst['name'][:20]}」退货率高达 {worst['return_rate']}%，退货金额 ¥{worst['return_amount']:,.0f}，建议立即检查产品质量和描述",
                "priority": "High",
                "target_type": "product",
            })

        if not recommendations:
            recommendations.append({
                "recommendation": "销售数据平稳，无异常需关注。建议持续监控核心指标趋势。",
                "priority": "Low",
                "target_type": "overall",
            })

        self._save_recommendations(recommendations)
        insights["recommendations"] = recommendations
        insights["agent_type"] = self.agent_type
        return insights


# ============================================================
# 2. Inventory Agent
# ============================================================
class InventoryAgent(BaseAgent):
    """库存分析Agent: 健康评分、缺货风险、滞销库存、资金占用."""

    agent_type = "Inventory Agent"

    def analyze(self, period: str, brand: Optional[str] = None) -> Dict[str, Any]:
        self._clear_old()
        recommendations = []
        insights = {}

        # --- 获取最新库存日期 ---
        latest_inv_date = self.db.query(func.max(Inventory.date)).scalar()
        if not latest_inv_date:
            insights["error"] = "No inventory data"
            insights["recommendations"] = []
            insights["agent_type"] = self.agent_type
            return insights

        # --- 库存明细 ---
        inv_q = (
            self.db.query(
                Product.id,
                Product.sku,
                Product.product_name,
                Product.brand,
                Product.unit_cost,
                func.sum(Inventory.available_qty).label("available"),
                func.sum(Inventory.reserved_qty).label("reserved"),
                func.sum(Inventory.inbound_qty).label("inbound"),
            )
            .join(Product, Inventory.product_id == Product.id)
            .filter(Inventory.date == latest_inv_date)
            .group_by(Product.id, Product.sku, Product.product_name, Product.brand, Product.unit_cost)
        )
        if brand:
            inv_q = inv_q.filter(Product.brand == brand)
        inv_results = inv_q.all()

        # --- 当月销售数据（计算日均销量）---
        start_date, end_date = period_to_date_range(period)
        days_in_period = (end_date - start_date).days + 1

        sales_q = (
            self.db.query(
                Product.id.label("product_id"),
                func.sum(SalesSummary.net_qty).label("qty"),
            )
            .join(Product, SalesSummary.product_id == Product.id)
            .filter(SalesSummary.period == period)
            .group_by(Product.id)
        )
        if brand:
            sales_q = sales_q.filter(Product.brand == brand)
        sales_map = {r.product_id: int(r.qty) if r.qty else 0 for r in sales_q.all()}

        # --- 分析每个SKU ---
        stockout_skus = []
        low_stock_skus = []
        stale_skus = []
        overstock_skus = []
        total_capital = 0.0
        healthy_count = 0

        for r in inv_results:
            available = int(r.available) if r.available else 0
            reserved = int(r.reserved) if r.reserved else 0
            inbound = int(r.inbound) if r.inbound else 0
            effective = available + inbound - reserved
            unit_cost = float(r.unit_cost) if r.unit_cost else 0

            sold_qty = sales_map.get(r.id, 0)
            daily_rate = sold_qty / days_in_period if days_in_period > 0 else 0
            capital = available * unit_cost
            total_capital += capital

            safety_stock = max(int(daily_rate * PROCUREMENT_DAYS * SAFETY_FACTOR_FAST), 5)

            sku_info = {
                "sku": r.sku,
                "name": r.product_name,
                "brand": r.brand,
                "available": available,
                "effective": effective,
                "daily_rate": round(daily_rate, 1),
                "safety_stock": safety_stock,
                "capital": round(capital, 2),
                "unit_cost": round(unit_cost, 2),
                "sold_qty": sold_qty,
            }

            if available == 0 and daily_rate > 0:
                stockout_skus.append(sku_info)
            elif available > 0 and available < safety_stock and daily_rate > 0:
                low_stock_skus.append(sku_info)
            elif available > STALE_STOCK_THRESHOLD and sold_qty < STALE_SALES_THRESHOLD:
                stale_skus.append(sku_info)
            elif daily_rate > 0 and available > 0:
                turnover_days = available / daily_rate if daily_rate > 0 else 999
                if turnover_days > 180:
                    overstock_skus.append({**sku_info, "turnover_days": round(turnover_days, 0)})
                else:
                    healthy_count += 1
            else:
                healthy_count += 1

        total_skus = len(inv_results)
        stockout_count = len(stockout_skus)
        low_count = len(low_stock_skus)
        stale_count = len(stale_skus)
        overstock_count = len(overstock_skus)

        # --- 健康评分 ---
        if total_skus > 0:
            health_score = int(
                100
                - (stockout_count / total_skus * 40)
                - (low_count / total_skus * 20)
                - (stale_count / total_skus * 20)
                - (overstock_count / total_skus * 20)
            )
            health_score = max(0, min(100, health_score))
        else:
            health_score = 0

        insights["summary"] = {
            "health_score": health_score,
            "total_skus": total_skus,
            "healthy_count": healthy_count,
            "stockout_count": stockout_count,
            "low_stock_count": low_count,
            "stale_count": stale_count,
            "overstock_count": overstock_count,
            "total_capital": round(total_capital, 2),
            "inv_date": str(latest_inv_date),
        }
        insights["stockout_skus"] = stockout_skus[:10]
        insights["low_stock_skus"] = low_stock_skus[:10]
        insights["stale_skus"] = stale_skus[:10]
        insights["overstock_skus"] = overstock_skus[:10]

        # --- 生成建议 ---
        if stockout_count > 0:
            top_stockout = stockout_skus[:3]
            names = ", ".join(s["name"][:15] for s in top_stockout)
            recommendations.append({
                "recommendation": f"{stockout_count}个SKU缺货（含{names}{'...' if stockout_count > 3 else ''}），日均销量正常但库存为0，正在损失销售机会，需立即补货",
                "priority": "High",
                "target_type": "product",
            })

        if low_count > 0:
            recommendations.append({
                "recommendation": f"{low_count}个SKU库存低于安全水位，预计 {PROCUREMENT_DAYS} 天内可能缺货，建议列入采购计划",
                "priority": "Medium",
                "target_type": "product",
            })

        if stale_count > 0:
            stale_capital = sum(s["capital"] for s in stale_skus)
            names = ", ".join(s["name"][:15] for s in stale_skus[:3])
            recommendations.append({
                "recommendation": f"{stale_count}个SKU库存积压（>50件且月销<5件），资金占用 ¥{stale_capital:,.0f}，建议促销清仓: {names}{'...' if stale_count > 3 else ''}",
                "priority": "Medium",
                "target_type": "product",
            })

        if overstock_count > 0:
            recommendations.append({
                "recommendation": f"{overstock_count}个SKU周转天数超过180天，库存过剩，建议控制后续采购量",
                "priority": "Low",
                "target_type": "product",
            })

        if health_score < 60:
            recommendations.append({
                "recommendation": f"库存健康评分仅 {health_score}/100，缺货和积压并存，建议全面梳理库存管理流程",
                "priority": "High",
                "target_type": "overall",
            })

        if not recommendations:
            recommendations.append({
                "recommendation": f"库存健康评分 {health_score}/100，整体状况良好。建议保持安全库存水位监控。",
                "priority": "Low",
                "target_type": "overall",
            })

        self._save_recommendations(recommendations)
        insights["recommendations"] = recommendations
        insights["agent_type"] = self.agent_type
        return insights


# ============================================================
# 3. Procurement Agent
# ============================================================
class ProcurementAgent(BaseAgent):
    """采购建议Agent: 补货建议、采购优先级、采购量.

    使用 reorder_service 统一引擎：
    - 近4个月加权日均销量（权重 4/3/2/1）
    - 采购周期 60 天（2个月）
    - 动态安全系数：周转<2个月→1.7，周转≥2个月→1.3
    """

    agent_type = "Procurement Agent"

    def analyze(self, period: str, brand: Optional[str] = None) -> Dict[str, Any]:
        self._clear_old()
        recommendations = []
        insights = {}

        # 调用统一补货引擎
        result = calculate_reorder(self.db, period, brand=brand)
        summary = result.get("summary", {})
        items = result.get("items", [])

        if summary.get("error"):
            insights["error"] = summary["error"]
            insights["recommendations"] = []
            insights["agent_type"] = self.agent_type
            return insights

        # 按优先级分组
        urgent_reorders = [i for i in items if i.get("priority") == "urgent"]
        normal_reorders = [i for i in items if i.get("priority") == "normal"]
        planned_reorders = [i for i in items if i.get("priority") == "planned"]

        total_urgent_value = sum(i.get("reorder_value", 0) for i in urgent_reorders)
        total_normal_value = sum(i.get("reorder_value", 0) for i in normal_reorders)

        insights["summary"] = {
            "urgent_count": len(urgent_reorders),
            "normal_count": len(normal_reorders),
            "planned_count": len(planned_reorders),
            "urgent_value": round(total_urgent_value, 2),
            "normal_value": round(total_normal_value, 2),
            "total_reorder_value": round(total_urgent_value + total_normal_value, 2),
            "total_reorder_qty": summary.get("total_reorder_qty", 0),
            "fast_moving_count": summary.get("fast_moving_count", 0),
            "slow_moving_count": summary.get("slow_moving_count", 0),
        }

        # 保留兼容旧格式的字段
        insights["urgent_reorders"] = [
            {
                "sku": i["sku"],
                "name": i["product_name"],
                "brand": i.get("brand"),
                "available": i["available_qty"],
                "inbound": i["inbound_qty"],
                "daily_rate": i["weighted_daily_rate"],
                "safety_stock": i["safety_stock"],
                "reorder_qty": i["reorder_qty"],
                "unit_cost": i["unit_cost"],
                "reorder_value": i["reorder_value"],
                "days_of_supply": i.get("days_of_supply", 0),
            }
            for i in urgent_reorders[:10]
        ]
        insights["normal_reorders"] = [
            {
                "sku": i["sku"],
                "name": i["product_name"],
                "brand": i.get("brand"),
                "available": i["available_qty"],
                "daily_rate": i["weighted_daily_rate"],
                "reorder_qty": i["reorder_qty"],
                "reorder_value": i["reorder_value"],
                "days_of_supply": i.get("days_of_supply", 0),
            }
            for i in normal_reorders[:10]
        ]

        # --- 建议 ---
        if urgent_reorders:
            top = urgent_reorders[0]
            recommendations.append({
                "recommendation": f"紧急补货 {len(urgent_reorders)} 个SKU，优先处理「{top['product_name'][:20]}」（库存{top['available_qty']}件，仅够{top.get('days_of_supply', 0)}天），预计采购金额 ¥{total_urgent_value:,.0f}",
                "priority": "High",
                "target_type": "product",
            })

        if normal_reorders:
            recommendations.append({
                "recommendation": f"常规补货 {len(normal_reorders)} 个SKU，预计采购金额 ¥{total_normal_value:,.0f}，建议本周内安排",
                "priority": "Medium",
                "target_type": "product",
            })

        total_value = total_urgent_value + total_normal_value
        if total_value > 0:
            recommendations.append({
                "recommendation": f"采购预算建议：¥{total_value:,.0f}（紧急 ¥{total_urgent_value:,.0f} + 常规 ¥{total_normal_value:,.0f}），基于近4个月加权日均销量计算，采购周期60天",
                "priority": "Medium",
                "target_type": "overall",
            })

        if not recommendations:
            recommendations.append({
                "recommendation": "当前库存充足，无紧急补货需求。建议定期复查安全库存水位。",
                "priority": "Low",
                "target_type": "overall",
            })

        self._save_recommendations(recommendations)
        insights["recommendations"] = recommendations
        insights["agent_type"] = self.agent_type
        return insights


# ============================================================
# 4. Finance Agent
# ============================================================
class FinanceAgent(BaseAgent):
    """财务分析Agent: 毛利、净利、亏损SKU、资金效率."""

    agent_type = "Finance Agent"

    def analyze(self, period: str, brand: Optional[str] = None) -> Dict[str, Any]:
        self._clear_old()
        recommendations = []
        insights = {}

        # --- 整体财务指标 ---
        q = (
            self.db.query(
                func.sum(SalesSummary.net_amount).label("revenue"),
                func.sum(SalesSummary.net_cost).label("cost"),
                func.sum(SalesSummary.net_profit).label("profit"),
                func.sum(SalesSummary.commission_cost).label("commission"),
                func.sum(SalesSummary.ship_amount).label("ship_amount"),
                func.sum(SalesSummary.ship_profit).label("ship_profit"),
            )
            .filter(SalesSummary.period == period)
        )
        q = self._apply_brand_filter(q, brand)
        s = q.first()

        revenue = float(s.revenue) if s.revenue else 0
        cost = float(s.cost) if s.cost else 0
        profit = float(s.profit) if s.profit else 0
        commission = float(s.commission) if s.commission else 0
        ship_amount = float(s.ship_amount) if s.ship_amount else 0
        ship_profit = float(s.ship_profit) if s.ship_profit else 0

        gross_margin = (profit / revenue * 100) if revenue > 0 else 0
        cost_ratio = (cost / revenue * 100) if revenue > 0 else 0
        commission_ratio = (commission / revenue * 100) if revenue > 0 else 0
        ship_margin = (ship_profit / ship_amount * 100) if ship_amount > 0 else 0

        insights["summary"] = {
            "revenue": round(revenue, 2),
            "cost": round(cost, 2),
            "profit": round(profit, 2),
            "commission": round(commission, 2),
            "gross_margin": round(gross_margin, 2),
            "cost_ratio": round(cost_ratio, 2),
            "commission_ratio": round(commission_ratio, 2),
            "ship_margin": round(ship_margin, 2),
        }

        # --- 按品牌分析 ---
        brand_q = (
            self.db.query(
                Product.brand,
                func.sum(SalesSummary.net_amount).label("revenue"),
                func.sum(SalesSummary.net_cost).label("cost"),
                func.sum(SalesSummary.net_profit).label("profit"),
            )
            .join(Product, SalesSummary.product_id == Product.id)
            .filter(SalesSummary.period == period)
            .group_by(Product.brand)
            .order_by(desc(func.sum(SalesSummary.net_amount)))
        )
        brand_results = brand_q.all()
        brand_data = []
        for r in brand_results:
            b_rev = float(r.revenue) if r.revenue else 0
            b_cost = float(r.cost) if r.cost else 0
            b_profit = float(r.profit) if r.profit else 0
            b_margin = (b_profit / b_rev * 100) if b_rev > 0 else 0
            brand_data.append({
                "brand": r.brand or "未分类",
                "revenue": round(b_rev, 2),
                "cost": round(b_cost, 2),
                "profit": round(b_profit, 2),
                "margin": round(b_margin, 2),
            })
        insights["by_brand"] = brand_data

        # --- 亏损SKU ---
        loss_q = (
            self.db.query(
                Product.sku,
                Product.product_name,
                Product.brand,
                func.sum(SalesSummary.net_amount).label("revenue"),
                func.sum(SalesSummary.net_cost).label("cost"),
                func.sum(SalesSummary.net_profit).label("profit"),
                func.sum(SalesSummary.net_qty).label("qty"),
            )
            .join(Product, SalesSummary.product_id == Product.id)
            .filter(SalesSummary.period == period)
            .group_by(Product.sku, Product.product_name, Product.brand)
            .having(func.sum(SalesSummary.net_profit) < 0)
            .order_by(func.sum(SalesSummary.net_profit).asc())
        )
        if brand:
            loss_q = loss_q.filter(Product.brand == brand)
        loss_results = loss_q.all()

        loss_skus = []
        total_loss = 0
        for r in loss_results:
            l_profit = float(r.profit) if r.profit else 0
            total_loss += l_profit
            loss_skus.append({
                "sku": r.sku,
                "name": r.product_name,
                "brand": r.brand,
                "qty": int(r.qty) if r.qty else 0,
                "revenue": round(float(r.revenue), 2) if r.revenue else 0,
                "cost": round(float(r.cost), 2) if r.cost else 0,
                "profit": round(l_profit, 2),
            })
        insights["loss_skus"] = loss_skus[:10]
        insights["total_loss"] = round(total_loss, 2)

        # --- 成本缺失分析 ---
        no_cost_q = (
            self.db.query(
                Product.sku,
                Product.product_name,
                func.sum(SalesSummary.net_amount).label("revenue"),
                func.sum(SalesSummary.net_qty).label("qty"),
            )
            .join(Product, SalesSummary.product_id == Product.id)
            .filter(SalesSummary.period == period)
            .filter(Product.unit_cost.is_(None))
            .group_by(Product.sku, Product.product_name)
            .order_by(desc(func.sum(SalesSummary.net_amount)))
        )
        no_cost_results = no_cost_q.all()
        no_cost_revenue = sum(float(r.revenue) if r.revenue else 0 for r in no_cost_results)
        insights["no_cost_sku_count"] = len(no_cost_results)
        insights["no_cost_revenue"] = round(no_cost_revenue, 2)

        # --- 建议 ---
        if gross_margin < 20:
            recommendations.append({
                "recommendation": f"整体毛利率仅 {gross_margin:.1f}%，利润空间极薄。建议审查成本结构和定价策略，或砍掉低毛利SKU",
                "priority": "High",
                "target_type": "overall",
            })
        elif gross_margin >= 60:
            recommendations.append({
                "recommendation": f"整体毛利率 {gross_margin:.1f}% 表现优秀，利润空间充足，可考虑加大营销投入扩大规模",
                "priority": "Medium",
                "target_type": "overall",
            })

        if loss_skus:
            recommendations.append({
                "recommendation": f"{len(loss_skus)}个SKU亏损，合计亏损 ¥{abs(total_loss):,.0f}，建议立即评估是否调价、控成本或下架",
                "priority": "High",
                "target_type": "product",
            })

        if no_cost_results:
            recommendations.append({
                "recommendation": f"{len(no_cost_results)}个SKU缺少成本数据（涉及销售额 ¥{no_cost_revenue:,.0f}），利润计算不准确，建议尽快补充成本信息",
                "priority": "High",
                "target_type": "overall",
            })

        if commission_ratio > 15:
            recommendations.append({
                "recommendation": f"佣金成本占销售额 {commission_ratio:.1f}%，偏高。建议与平台谈判佣金费率或优化渠道结构",
                "priority": "Medium",
                "target_type": "overall",
            })

        # 品牌利润对比
        if len(brand_data) >= 2:
            best_brand = max(brand_data, key=lambda x: x["margin"])
            worst_brand = min(brand_data, key=lambda x: x["margin"])
            if best_brand["margin"] - worst_brand["margin"] > 30:
                recommendations.append({
                    "recommendation": f"品牌利润差异大：「{best_brand['brand']}」毛利率 {best_brand['margin']:.1f}% vs「{worst_brand['brand']}」{worst_brand['margin']:.1f}%，建议优化低毛利品牌成本结构",
                    "priority": "Medium",
                    "target_type": "overall",
                })

        if not recommendations:
            recommendations.append({
                "recommendation": f"财务状况健康，毛利率 {gross_margin:.1f}%。建议持续监控成本结构变化。",
                "priority": "Low",
                "target_type": "overall",
            })

        self._save_recommendations(recommendations)
        insights["recommendations"] = recommendations
        insights["agent_type"] = self.agent_type
        return insights


# ============================================================
# 5. Operation Agent
# ============================================================
class OperationAgent(BaseAgent):
    """运营优化Agent: 定价、促销、折扣分析."""

    agent_type = "Operation Agent"

    def analyze(self, period: str, brand: Optional[str] = None) -> Dict[str, Any]:
        self._clear_old()
        recommendations = []
        insights = {}

        # --- 折扣/定价分析 ---
        q = (
            self.db.query(
                func.sum(SalesSummary.ship_amount).label("ship_amount"),
                func.sum(SalesSummary.net_amount).label("net_amount"),
                func.sum(SalesSummary.net_profit).label("profit"),
                func.sum(SalesSummary.ship_qty).label("ship_qty"),
                func.sum(SalesSummary.net_qty).label("net_qty"),
            )
            .filter(SalesSummary.period == period)
        )
        q = self._apply_brand_filter(q, brand)
        s = q.first()

        ship_amount = float(s.ship_amount) if s.ship_amount else 0
        net_amount = float(s.net_amount) if s.net_amount else 0
        profit = float(s.profit) if s.profit else 0
        ship_qty = int(s.ship_qty) if s.ship_qty else 0
        net_qty = int(s.net_qty) if s.net_qty else 0

        discount_amount = ship_amount - net_amount
        discount_rate = (discount_amount / ship_amount * 100) if ship_amount > 0 else 0
        avg_order_value = (net_amount / net_qty) if net_qty > 0 else 0

        insights["summary"] = {
            "ship_amount": round(ship_amount, 2),
            "net_amount": round(net_amount, 2),
            "discount_amount": round(discount_amount, 2),
            "discount_rate": round(discount_rate, 2),
            "profit": round(profit, 2),
            "ship_qty": ship_qty,
            "net_qty": net_qty,
            "avg_order_value": round(avg_order_value, 2),
        }

        # --- 低毛利SKU（定价建议）---
        low_margin_q = (
            self.db.query(
                Product.sku,
                Product.product_name,
                Product.brand,
                func.sum(SalesSummary.net_amount).label("revenue"),
                func.sum(SalesSummary.net_cost).label("cost"),
                func.sum(SalesSummary.net_profit).label("profit"),
                func.sum(SalesSummary.net_qty).label("qty"),
            )
            .join(Product, SalesSummary.product_id == Product.id)
            .filter(SalesSummary.period == period)
            .group_by(Product.sku, Product.product_name, Product.brand)
            .having(func.sum(SalesSummary.net_amount) > 500)
            .order_by(func.sum(SalesSummary.net_profit).asc())
        )
        if brand:
            low_margin_q = low_margin_q.filter(Product.brand == brand)
        low_margin_results = low_margin_q.all()

        low_margin_skus = []
        for r in low_margin_results:
            r_rev = float(r.revenue) if r.revenue else 0
            r_cost = float(r.cost) if r.cost else 0
            r_profit = float(r.profit) if r.profit else 0
            r_qty = int(r.qty) if r.qty else 0
            margin = (r_profit / r_rev * 100) if r_rev > 0 else 0
            if margin < 30 and r_rev > 500:
                suggested_price = r_cost / 0.6 if r_cost > 0 else 0  # 目标60%毛利
                low_margin_skus.append({
                    "sku": r.sku,
                    "name": r.product_name,
                    "brand": r.brand,
                    "qty": r_qty,
                    "revenue": round(r_rev, 2),
                    "cost": round(r_cost, 2),
                    "profit": round(r_profit, 2),
                    "margin": round(margin, 1),
                    "suggested_price": round(suggested_price / r_qty, 2) if r_qty > 0 else 0,
                })
        insights["low_margin_skus"] = low_margin_skus[:10]

        # --- 促销机会（滞销库存 + 高毛利）---
        latest_inv_date = self.db.query(func.max(Inventory.date)).scalar()
        promo_opportunities = []
        if latest_inv_date:
            stale_q = (
                self.db.query(
                    Product.sku,
                    Product.product_name,
                    Product.brand,
                    func.sum(Inventory.available_qty).label("available"),
                    Product.unit_cost,
                )
                .join(Product, Inventory.product_id == Product.id)
                .filter(Inventory.date == latest_inv_date)
                .group_by(Product.id, Product.sku, Product.product_name, Product.brand, Product.unit_cost)
                .having(func.sum(Inventory.available_qty) > STALE_STOCK_THRESHOLD)
            )
            if brand:
                stale_q = stale_q.filter(Product.brand == brand)
            stale_results = stale_q.all()

            sales_q = (
                self.db.query(
                    Product.id.label("pid"),
                    func.sum(SalesSummary.net_qty).label("qty"),
                    func.sum(SalesSummary.net_amount).label("rev"),
                )
                .join(Product, SalesSummary.product_id == Product.id)
                .filter(SalesSummary.period == period)
                .group_by(Product.id)
            )
            if brand:
                sales_q = sales_q.filter(Product.brand == brand)
            sales_map = {r.pid: (int(r.qty) if r.qty else 0, float(r.rev) if r.rev else 0) for r in sales_q.all()}

            # 需要联查product id
            stale_with_id_q = (
                self.db.query(
                    Product.id,
                    Product.sku,
                    Product.product_name,
                    Product.brand,
                    Product.unit_cost,
                    func.sum(Inventory.available_qty).label("available"),
                )
                .join(Product, Inventory.product_id == Product.id)
                .filter(Inventory.date == latest_inv_date)
                .group_by(Product.id, Product.sku, Product.product_name, Product.brand, Product.unit_cost)
                .having(func.sum(Inventory.available_qty) > STALE_STOCK_THRESHOLD)
            )
            if brand:
                stale_with_id_q = stale_with_id_q.filter(Product.brand == brand)
            stale_with_id_results = stale_with_id_q.all()

            for r in stale_with_id_results:
                sold_qty, sold_rev = sales_map.get(r.id, (0, 0))
                if sold_qty < STALE_SALES_THRESHOLD:
                    available = int(r.available) if r.available else 0
                    unit_cost = float(r.unit_cost) if r.unit_cost else 0
                    capital = available * unit_cost
                    promo_opportunities.append({
                        "sku": r.sku,
                        "name": r.product_name,
                        "brand": r.brand,
                        "available": available,
                        "capital": round(capital, 2),
                        "monthly_sales": sold_qty,
                        "suggested_action": "限时折扣/捆绑销售" if capital > 5000 else "优惠券清仓",
                    })

        promo_opportunities.sort(key=lambda x: x["capital"], reverse=True)
        insights["promo_opportunities"] = promo_opportunities[:10]

        # --- 建议 ---
        if discount_rate > 25:
            recommendations.append({
                "recommendation": f"折扣率 {discount_rate:.1f}%（折扣金额 ¥{discount_amount:,.0f}），过度折扣侵蚀利润。建议优化折扣策略，减少无差别满减",
                "priority": "High",
                "target_type": "overall",
            })
        elif discount_rate > 15:
            recommendations.append({
                "recommendation": f"折扣率 {discount_rate:.1f}%，处于较高水平。建议监控折扣对利润的实际影响",
                "priority": "Medium",
                "target_type": "overall",
            })

        if low_margin_skus:
            top = low_margin_skus[0]
            recommendations.append({
                "recommendation": f"{len(low_margin_skus)}个SKU毛利率低于30%，其中「{top['name'][:20]}」仅 {top['margin']}%，建议涨价至 ¥{top['suggested_price']}/件或优化成本",
                "priority": "High",
                "target_type": "product",
            })

        if promo_opportunities:
            total_stale_capital = sum(p["capital"] for p in promo_opportunities)
            recommendations.append({
                "recommendation": f"{len(promo_opportunities)}个SKU库存积压（资金占用 ¥{total_stale_capital:,.0f}），建议启动限时促销或捆绑销售加速资金回笼",
                "priority": "Medium",
                "target_type": "product",
            })

        if avg_order_value > 0:
            recommendations.append({
                "recommendation": f"客单价 ¥{avg_order_value:.1f}，建议通过关联推荐、满减门槛设计提升客单价",
                "priority": "Low",
                "target_type": "overall",
            })

        if not recommendations:
            recommendations.append({
                "recommendation": "运营指标正常，折扣和定价策略合理。建议持续优化产品结构和渠道效率。",
                "priority": "Low",
                "target_type": "overall",
            })

        self._save_recommendations(recommendations)
        insights["recommendations"] = recommendations
        insights["agent_type"] = self.agent_type
        return insights


# ============================================================
# 6. CEO Agent
# ============================================================
class CEOAgent(BaseAgent):
    """CEO决策Agent: 汇总所有Agent，生成3个问题+3个动作."""

    agent_type = "CEO Agent"

    def analyze(self, period: str, brand: Optional[str] = None) -> Dict[str, Any]:
        self._clear_old()

        # --- 运行所有子Agent ---
        sales = SalesAgent(self.db).analyze(period, brand)
        inventory = InventoryAgent(self.db).analyze(period, brand)
        procurement = ProcurementAgent(self.db).analyze(period, brand)
        finance = FinanceAgent(self.db).analyze(period, brand)
        operation = OperationAgent(self.db).analyze(period, brand)

        agent_results = {
            "sales": sales,
            "inventory": inventory,
            "procurement": procurement,
            "finance": finance,
            "operation": operation,
        }

        # --- 提取核心指标 ---
        sales_s = sales.get("summary", {})
        inv_s = inventory.get("summary", {})
        fin_s = finance.get("summary", {})
        op_s = operation.get("summary", {})
        proc_s = procurement.get("summary", {})

        revenue = sales_s.get("revenue", 0)
        profit = sales_s.get("profit", 0)
        gross_margin = fin_s.get("gross_margin", 0)
        return_rate = sales_s.get("return_rate", 0)
        ship_qty = sales_s.get("ship_qty", 0)
        stockout_count = inv_s.get("stockout_count", 0)
        stale_count = inv_s.get("stale_count", 0)
        health_score = inv_s.get("health_score", 0)
        loss_count = len(finance.get("loss_skus", []))
        total_loss = finance.get("total_loss", 0)
        urgent_reorder_count = proc_s.get("urgent_count", 0)
        urgent_reorder_value = proc_s.get("urgent_value", 0)
        discount_rate = op_s.get("discount_rate", 0)
        no_cost_count = finance.get("no_cost_sku_count", 0)
        mom = sales.get("mom")

        # --- 汇总所有High优先级建议 ---
        all_high_recs = []
        for agent_name, result in agent_results.items():
            for rec in result.get("recommendations", []):
                if rec.get("priority") == "High":
                    all_high_recs.append({
                        "agent": agent_name,
                        "text": rec["recommendation"],
                    })

        # --- 生成3个关键问题 ---
        questions = []

        if stockout_count > 0:
            questions.append(f"{stockout_count}个SKU缺货正在损失销售，为什么没有及时补货？采购流程哪里卡住了？")
        elif urgent_reorder_count > 0:
            questions.append(f"{urgent_reorder_count}个SKU急需补货（采购金额 ¥{urgent_reorder_value:,.0f}），资金和供应商交期是否到位？")

        if loss_count > 0:
            questions.append(f"{loss_count}个SKU亏损合计 ¥{abs(total_loss):,.0f}，这些产品是否还有存在的必要？是定价问题还是成本问题？")
        elif gross_margin < 30:
            questions.append(f"整体毛利率仅 {gross_margin:.1f}%，利润空间不足，成本结构哪里可以优化？")

        if return_rate > 10:
            questions.append(f"退货率 {return_rate:.1f}% 偏高，退货金额 ¥{sales_s.get('revenue', 0) * return_rate / 100:,.0f}，根因是产品质量还是描述不符？")
        elif stale_count > 0:
            questions.append(f"{stale_count}个SKU库存积压，资金被无效占用，清仓计划为什么没有执行？")

        if no_cost_count > 0:
            questions.append(f"{no_cost_count}个SKU缺少成本数据，利润计算不准确，成本管理流程哪里断了？")

        if mom and mom.get("revenue_change_pct", 0) < -10:
            questions.append(f"销售额环比下降 {abs(mom['revenue_change_pct'])}%，是市场变化还是自身运营问题？")

        # 补足到3个
        if len(questions) < 3:
            if discount_rate > 20:
                questions.append(f"折扣率 {discount_rate:.1f}% 偏高，折扣是否真正带来了增量利润还是只是侵蚀毛利？")
            if health_score < 70:
                questions.append(f"库存健康评分 {health_score}/100，库存管理是否需要系统性改进？")
            if revenue > 0:
                questions.append(f"月销售额 ¥{revenue:,.0f}，利润 ¥{profit:,.0f}，下一步增长从哪里来——扩品、扩渠道还是提客单？")

        questions = questions[:3]

        # --- 生成3个建议动作 ---
        actions = []

        if stockout_count > 0 or urgent_reorder_count > 0:
            total_urg = stockout_count + urgent_reorder_count
            actions.append(f"立即启动紧急采购流程：{total_urg}个SKU缺货或即将缺货，预计采购 ¥{urgent_reorder_value:,.0f}，48小时内下单")

        if loss_count > 0:
            actions.append(f"本周内完成亏损SKU评估：{loss_count}个SKU合计亏损 ¥{abs(total_loss):,.0f}，逐个决定调价/控成本/下架")

        if stale_count > 0:
            stale_capital = sum(s.get("capital", 0) for s in inventory.get("stale_skus", []))
            actions.append(f"启动库存清仓计划：{stale_count}个SKU积压，资金占用 ¥{stale_capital:,.0f}，限时折扣+捆绑销售")

        if return_rate > 10:
            actions.append(f"召开退货根因分析会：退货率 {return_rate:.1f}%，3天内定位Top3高退货SKU的问题并出整改方案")

        if no_cost_count > 0:
            actions.append(f"补充成本数据：{no_cost_count}个SKU缺失成本，涉及销售额 ¥{finance.get('no_cost_revenue', 0):,.0f}，1周内补齐")

        if gross_margin < 30 and not any("调价" in a for a in actions):
            actions.append("启动定价审查：整体毛利率偏低，对所有毛利率<30%的SKU重新评估定价和成本")

        # 补足到3个
        if len(actions) < 3:
            if revenue > 0 and profit > 0 and gross_margin > 50:
                actions.append("利润状况健康，建议加大广告投放扩大规模，重点推广Top3 SKU")
            if mom and mom.get("revenue_change_pct", 0) > 20:
                actions.append("销售额增长强劲，分析增长驱动因素并固化成功经验，趁势扩大优势")
            if health_score >= 80 and gross_margin >= 40:
                actions.append("经营状况良好，建议制定下月增长目标：销售额+15%，重点提升客单价和复购率")

        actions = actions[:3]

        # --- 执行摘要 ---
        if health_score >= 80 and gross_margin >= 40 and stockout_count == 0:
            overall_status = "excellent"
            status_text = "经营状况优秀"
        elif stockout_count > 5 or gross_margin < 20 or return_rate > 15:
            overall_status = "critical"
            status_text = "存在严重风险，需立即干预"
        elif loss_count > 5 or health_score < 60 or return_rate > 10:
            overall_status = "warning"
            status_text = "存在风险隐患，需重点关注"
        else:
            overall_status = "normal"
            status_text = "经营状况正常，持续优化"

        ceo_summary = {
            "overall_status": overall_status,
            "status_text": status_text,
            "revenue": round(revenue, 2),
            "profit": round(profit, 2),
            "gross_margin": round(gross_margin, 2),
            "return_rate": round(return_rate, 2),
            "ship_qty": ship_qty,
            "stockout_count": stockout_count,
            "loss_count": loss_count,
            "total_loss": round(total_loss, 2),
            "stale_count": stale_count,
            "health_score": health_score,
            "urgent_reorder_count": urgent_reorder_count,
            "urgent_reorder_value": round(urgent_reorder_value, 2),
            "no_cost_count": no_cost_count,
            "discount_rate": round(discount_rate, 2),
            "period": period,
        }

        if mom:
            ceo_summary["mom_revenue_change"] = mom.get("revenue_change_pct")

        # --- 保存CEO建议 ---
        ceo_recs = []
        for q in questions:
            ceo_recs.append({
                "recommendation": f"[关键问题] {q}",
                "priority": "High",
                "target_type": "overall",
            })
        for a in actions:
            ceo_recs.append({
                "recommendation": f"[建议动作] {a}",
                "priority": "High",
                "target_type": "overall",
            })
        self._save_recommendations(ceo_recs)

        return {
            "agent_type": self.agent_type,
            "summary": ceo_summary,
            "questions": questions,
            "actions": actions,
            "high_priority_alerts": all_high_recs,
            "agent_results": agent_results,
        }


# ============================================================
# Runner
# ============================================================
def run_all_agents(db: Session, period: Optional[str] = None, brand: Optional[str] = None) -> Dict[str, Any]:
    """Run all 6 agents and return combined results."""
    if not period:
        period = get_latest_period(db)

    ceo = CEOAgent(db).analyze(period, brand)

    return {
        "period": period,
        "brand": brand,
        "ceo": ceo,
        "agents": {
            "sales": ceo["agent_results"]["sales"],
            "inventory": ceo["agent_results"]["inventory"],
            "procurement": ceo["agent_results"]["procurement"],
            "finance": ceo["agent_results"]["finance"],
            "operation": ceo["agent_results"]["operation"],
        },
    }


def get_saved_recommendations(
    db: Session,
    agent_type: Optional[str] = None,
    priority: Optional[str] = None,
    limit: int = 50,
) -> List[Dict[str, Any]]:
    """Get saved recommendations from ai_recommendations table."""
    q = db.query(AIRecommendation)
    if agent_type:
        q = q.filter(AIRecommendation.agent_type == agent_type)
    if priority:
        q = q.filter(AIRecommendation.priority == priority)
    q = q.order_by(desc(AIRecommendation.created_at)).limit(limit)
    results = q.all()

    return [
        {
            "id": str(r.id),
            "agent_type": r.agent_type,
            "recommendation": r.recommendation,
            "priority": r.priority,
            "target_type": r.target_type,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in results
    ]
