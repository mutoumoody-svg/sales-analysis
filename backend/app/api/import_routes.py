"""
Import routes v2 - 数据导入接口
==============================
适配新旺店通数据结构（2026-07起统一格式）。

端点：
- POST /import/detail     销售出库明细表导入（94列，含成本/毛利）
- POST /import/summary    货品销售汇总表导入（23列，店铺×货品维度）
- POST /import/inventory  库存文件导入（多Sheet）
- POST /import/all        批量导入（明细+汇总+库存）
- GET  /import/status     查询数据库当前数据量
"""

import os
import tempfile
from datetime import date
from typing import Dict, Optional

from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, Form
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.database import get_db
from app.services.import_service import (
    import_sales_detail,
    import_sales_summary,
    import_inventory,
    import_all,
)

router = APIRouter()

ALLOWED_EXTENSIONS = [".xlsx", ".xls", ".csv"]


def _validate_file(file: UploadFile) -> str:
    """验证上传的文件，返回文件扩展名。"""
    if not file.filename:
        raise HTTPException(status_code=400, detail="未提供文件")
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件类型: {ext}。允许: {ALLOWED_EXTENSIONS}",
        )
    return ext


async def _save_upload(file: UploadFile) -> str:
    """将上传的文件保存到临时路径，返回路径。"""
    ext = _validate_file(file)
    fd, tmp_path = tempfile.mkstemp(suffix=ext, prefix="import_")
    os.close(fd)
    with open(tmp_path, "wb") as f:
        content = await file.read()
        f.write(content)
    return tmp_path


def _cleanup(path: str):
    """清理临时文件。"""
    try:
        if path and os.path.exists(path):
            os.remove(path)
    except Exception:
        pass


# ============================================
# 销售出库明细表导入
# ============================================
@router.post("/import/detail")
async def import_detail(
    file: UploadFile = File(...),
    sheet_name: Optional[str] = Form(None, description="Sheet名称，不传则自动检测第一个Sheet"),
    period: Optional[str] = Form(None, description="会计期间 YYYY-MM，仅用于记录"),
    db: Session = Depends(get_db),
) -> Dict:
    """上传旺店通销售出库明细表 Excel 文件并导入。

    - 支持 .xlsx / .xls / .csv
    - 不指定sheet_name时自动检测第一个Sheet
    - 自动过滤"合计:"行
    - 导入成本/毛利数据到 OrderItem + Order
    - 自动创建店铺、商品、客户记录（去重）
    - 按订单号分组：一个订单号 → 一个 order + 多个 order_items
    - 明细数据日期来自"下单时间"列，period仅用于记录/显示
    """
    tmp_path = await _save_upload(file)
    try:
        result = import_sales_detail(db, tmp_path, sheet_name=sheet_name, period=period)
        return {
            "status": "success" if not result.errors else "partial",
            "message": f"导入完成: {result.processed} 行处理, {result.skipped} 行跳过, {result.filtered_total_rows} 合计行过滤",
            "data": result.to_dict(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导入失败: {str(e)}")
    finally:
        _cleanup(tmp_path)


# ============================================
# 货品销售汇总表导入
# ============================================
@router.post("/import/summary")
async def import_summary(
    file: UploadFile = File(...),
    sheet_name: str = Form("Sheet1"),
    period: Optional[str] = Form(None, description="会计期间 YYYY-MM，不传则从文件名推断"),
    db: Session = Depends(get_db),
) -> Dict:
    """上传旺店通货品销售汇总表 Excel 文件并导入。

    - 按店铺×货品×月份维度汇总
    - 包含发货/退货/实际销售的数量、金额、成本、利润
    - upsert模式：同店铺×商品×月份已存在则更新
    - 自动过滤合计行和空货品行
    - period 不传则从文件名中提取年月（如 2607xxx → 2026-07）
    """
    tmp_path = await _save_upload(file)
    try:
        result = import_sales_summary(db, tmp_path, sheet_name=sheet_name, period=period)
        return {
            "status": "success" if not result.errors else "partial",
            "message": f"导入完成: {result.processed} 行处理, {result.summary_records} 条汇总记录, {result.skipped} 行跳过",
            "data": result.to_dict(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导入失败: {str(e)}")
    finally:
        _cleanup(tmp_path)


# ============================================
# 库存文件导入
# ============================================
@router.post("/import/inventory")
async def import_inventory_route(
    file: UploadFile = File(...),
    snapshot_date: Optional[str] = Form(None),
    db: Session = Depends(get_db),
) -> Dict:
    """上传旺店通库存文件 Excel 并导入。

    - 自动遍历所有商品类 Sheet（跳过预警 Sheet）
    - 每个仓库列分别创建库存记录
    - snapshot_date 不传则用今天
    """
    tmp_path = await _save_upload(file)
    try:
        result = import_inventory(db, tmp_path, snapshot_date=snapshot_date)
        return {
            "status": "success" if not result.errors else "partial",
            "message": f"导入完成: {result.processed} 行处理, {result.inventory_records} 条库存记录",
            "data": result.to_dict(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导入失败: {str(e)}")
    finally:
        _cleanup(tmp_path)


# ============================================
# 批量导入
# ============================================
@router.post("/import/all")
async def import_all_route(
    detail_file: UploadFile = File(None),
    summary_file: UploadFile = File(None),
    inventory_file: UploadFile = File(None),
    period: Optional[str] = Form(None, description="会计期间 YYYY-MM"),
    db: Session = Depends(get_db),
) -> Dict:
    """批量导入：可同时上传明细、汇总、库存三个文件。

    三个文件参数都是可选的，只上传需要的即可。
    period 用于汇总表的月份标记。
    """
    paths = {}

    try:
        if detail_file and detail_file.filename:
            paths["detail"] = await _save_upload(detail_file)
        if summary_file and summary_file.filename:
            paths["summary"] = await _save_upload(summary_file)
        if inventory_file and inventory_file.filename:
            paths["inventory"] = await _save_upload(inventory_file)

        if not paths:
            raise HTTPException(status_code=400, detail="未提供任何文件")

        results = import_all(
            db,
            detail_file=paths.get("detail"),
            summary_file=paths.get("summary"),
            inventory_file=paths.get("inventory"),
            period=period,
        )
        return {
            "status": "success",
            "message": f"批量导入完成: {list(paths.keys())}",
            "data": results,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"导入失败: {str(e)}")
    finally:
        for p in paths.values():
            _cleanup(p)


# ============================================
# 数据库状态查询
# ============================================
@router.get("/import/status")
async def get_import_status(db: Session = Depends(get_db)) -> Dict:
    """查询各表当前数据量，用于确认导入结果。"""
    tables = [
        "stores",
        "products",
        "customers",
        "orders",
        "order_items",
        "sales_summary",
        "inventory",
        "expenses",
        "profit_analysis",
        "ai_recommendations",
    ]
    counts = {}
    for t in tables:
        try:
            r = db.execute(text(f"SELECT count(*) FROM {t}"))
            counts[t] = r.fetchone()[0]
        except Exception:
            counts[t] = 0

    return {
        "status": "success",
        "data": {
            "table_counts": counts,
            "total_records": sum(counts.values()),
        },
    }
