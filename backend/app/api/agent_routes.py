"""
Agent routes - AI Agent analysis API.
Provides endpoints to run agents and get recommendations.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from typing import Dict, Optional

from app.database import get_db
from app.services.agent_service import (
    run_all_agents,
    get_saved_recommendations,
    SalesAgent,
    InventoryAgent,
    ProcurementAgent,
    FinanceAgent,
    OperationAgent,
    CEOAgent,
)
from app.utils.period import resolve_period, get_latest_period

router = APIRouter()


@router.get("/agents/run")
def run_agents(
    brand: Optional[str] = Query(None, description="品牌筛选"),
    month: Optional[str] = Query(None, description="月份 YYYY-MM"),
    db: Session = Depends(get_db),
) -> Dict:
    """运行全部6个Agent，返回完整分析结果."""
    period = resolve_period(db, month)
    result = run_all_agents(db, period=period, brand=brand)
    return {"status": "success", "data": result}


@router.get("/agents/ceo-report")
def agent_ceo_report(
    brand: Optional[str] = Query(None, description="品牌筛选"),
    month: Optional[str] = Query(None, description="月份 YYYY-MM"),
    db: Session = Depends(get_db),
) -> Dict:
    """获取CEO Agent报告（汇总所有Agent）."""
    period = resolve_period(db, month)
    result = CEOAgent(db).analyze(period, brand)
    return {"status": "success", "data": result}


@router.get("/agents/sales")
def agent_sales(
    brand: Optional[str] = Query(None, description="品牌筛选"),
    month: Optional[str] = Query(None, description="月份 YYYY-MM"),
    db: Session = Depends(get_db),
) -> Dict:
    """销售Agent分析."""
    period = resolve_period(db, month)
    result = SalesAgent(db).analyze(period, brand)
    return {"status": "success", "data": result}


@router.get("/agents/inventory")
def agent_inventory(
    brand: Optional[str] = Query(None, description="品牌筛选"),
    month: Optional[str] = Query(None, description="月份 YYYY-MM"),
    db: Session = Depends(get_db),
) -> Dict:
    """库存Agent分析."""
    period = resolve_period(db, month)
    result = InventoryAgent(db).analyze(period, brand)
    return {"status": "success", "data": result}


@router.get("/agents/procurement")
def agent_procurement(
    brand: Optional[str] = Query(None, description="品牌筛选"),
    month: Optional[str] = Query(None, description="月份 YYYY-MM"),
    db: Session = Depends(get_db),
) -> Dict:
    """采购Agent分析."""
    period = resolve_period(db, month)
    result = ProcurementAgent(db).analyze(period, brand)
    return {"status": "success", "data": result}


@router.get("/agents/finance")
def agent_finance(
    brand: Optional[str] = Query(None, description="品牌筛选"),
    month: Optional[str] = Query(None, description="月份 YYYY-MM"),
    db: Session = Depends(get_db),
) -> Dict:
    """财务Agent分析."""
    period = resolve_period(db, month)
    result = FinanceAgent(db).analyze(period, brand)
    return {"status": "success", "data": result}


@router.get("/agents/operation")
def agent_operation(
    brand: Optional[str] = Query(None, description="品牌筛选"),
    month: Optional[str] = Query(None, description="月份 YYYY-MM"),
    db: Session = Depends(get_db),
) -> Dict:
    """运营Agent分析."""
    period = resolve_period(db, month)
    result = OperationAgent(db).analyze(period, brand)
    return {"status": "success", "data": result}


@router.get("/agents/recommendations")
def get_recommendations(
    agent_type: Optional[str] = Query(None, description="Agent类型筛选"),
    priority: Optional[str] = Query(None, description="优先级筛选 High/Medium/Low"),
    limit: int = Query(50, description="返回数量"),
    db: Session = Depends(get_db),
) -> Dict:
    """获取已保存的AI建议列表."""
    result = get_saved_recommendations(db, agent_type=agent_type, priority=priority, limit=limit)
    return {"status": "success", "data": result}
