"""
Wangdiantong Sync Service - 从旺店通ERP API 同步实时库存到 sales-analysis.

数据流:
    旺店通API (stock_query.php) → wangdian_client.py 拉取 → 映射 → upsert inventory 表

与 kucun 同步的区别:
    - kucun: 手动上传 Excel → JSON 文件 → 读取同步（被动）
    - 旺店通: API 直连 → 自动拉取（主动），数据更实时、字段更丰富

字段映射:
    旺店通 spec_no (商家编码) → Product.sku → Inventory.product_id
    旺店通 warehouse_name → Inventory.warehouse
    旺店通 stock_num (库存量) → Inventory.available_qty
    旺店通 lock_num + unpay_num + order_num + sending_num → Inventory.reserved_qty
    旺店通 purchase_num + transfer_num → Inventory.inbound_qty

接口说明:
    使用 stock_query.php，无调用时间限制，可随时调用。
    仅拉取最近30天有变动的库存记录（单窗口，快速获取当前库存快照）。

仓库白名单:
    只同步核心仓库（与 kucun 系统一致），过滤线下门店/书店/展会等噪音仓库。
    WAREHOUSE_WHITELIST 可在代码中扩展，未来新增仓库只需加入此集合。

幂等性:
    按 (product_id, warehouse) 原地更新：找到现有记录就更新数量+date=today，
    找不到就插入。不会跨天累积重复记录。
"""

import json
from pathlib import Path
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple

from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.inventory import Inventory
from app.models.product import Product
from app.services.wangdian_client import WangdianClient, WangdianAPIError


# ===== 同步元数据存储 =====
WANGDIAN_SYNC_META_FILE = Path("/opt/sales-analysis/.wangdian_sync_meta.json")

# ===== 仓库白名单 =====
# 只同步核心仓库（与 kucun 系统一致），过滤线下门店/书店/展会等噪音仓库
# 未来新增仓库只需加入此集合
WAREHOUSE_WHITELIST = {"美乐印刷", "速易正品仓", "速易瑞福兰仓"}


def _read_sync_meta() -> Dict:
    """读上次同步元数据."""
    if WANGDIAN_SYNC_META_FILE.exists():
        try:
            return json.loads(WANGDIAN_SYNC_META_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _write_sync_meta(meta: Dict) -> None:
    """写同步元数据."""
    try:
        WANGDIAN_SYNC_META_FILE.parent.mkdir(parents=True, exist_ok=True)
        WANGDIAN_SYNC_META_FILE.write_text(
            json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except Exception:
        pass


# ===== 品牌映射 =====
# 旺店通 brand_name → sales-analysis products.brand
WANGDIAN_BRAND_MAP = {
    "STTOKE": "慕咖STTOKE",
    "慕咖": "慕咖（MOODY）",
    "MOODY": "慕咖（MOODY）",
    "巴恩": "巴恩天然",
    "巴恩天然": "巴恩天然",
    "MoodyCoffee": "MoodyCoffee",
    "康蜜乐": "康蜜乐 CAPILANO",
    "CAPILANO": "康蜜乐 CAPILANO",
}


def _normalize_brand(brand_name: str) -> str:
    """将旺店通品牌名映射到 sales-analysis 品牌值."""
    if not brand_name:
        return "其他"
    b = str(brand_name).strip()
    if b in WANGDIAN_BRAND_MAP:
        return WANGDIAN_BRAND_MAP[b]
    for key, val in WANGDIAN_BRAND_MAP.items():
        if key.lower() in b.lower() or b.lower() in key.lower():
            return val
    return "其他"


# ===== 核心同步逻辑 =====

def sync_from_wangdian(
    db: Session,
    sid: str,
    appkey: str,
    appsecret: str,
    sandbox: bool = False,
) -> Dict:
    """从旺店通API拉取全量库存，同步到 sales-analysis inventory 表.

    Args:
        db: 数据库会话
        sid: 旺店通卖家账号
        appkey: 旺店通接口账号
        appsecret: 旺店通接口密钥
        sandbox: 是否使用测试环境

    Returns:
        {
            "status": "success" | "error",
            "message": "...",
            "synced_date": "2026-08-08",
            "total_from_api": 1200,
            "matched_count": 1180,
            "auto_created": 20,
            "inserted": 800,
            "updated": 380,
            "unchanged": 20,
            "warehouse_count": 5,
            "last_sync_at": "...",
        }
    """
    # 使用 stock_query.php，无时间限制
    client = WangdianClient(sid=sid, appkey=appkey, appsecret=appsecret, sandbox=sandbox)

    # 仅拉取最近30天有变动的库存记录（单窗口，快速获取当前库存快照）
    # 历史数据不需要，只要实时/前一天的库存数量即可
    now = datetime.now()
    start_time = (now - timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")
    end_time = now.strftime("%Y-%m-%d %H:%M:%S")
    sync_date = now.date()

    try:
        stocks_data, total_count = client.query_all_stock(
            start_time=start_time,
            end_time=end_time,
            page_size=100,
        )
    except WangdianAPIError as e:
        return {
            "status": "error",
            "message": f"旺店通API调用失败: {e.message}（错误码: {e.code}）",
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"旺店通API调用异常: {str(e)}",
        }

    if not stocks_data:
        return {
            "status": "error",
            "message": "旺店通API返回空数据，请检查sid/appkey/appsecret是否正确",
        }

    # 加载 products 表 SKU → id 映射
    products = db.query(Product.sku, Product.id).all()
    sku_to_id = {sku: pid for sku, pid in products if sku}

    # 遍历 API 数据，映射到 inventory 记录
    # 按 (warehouse, product_id) 聚合（同一SKU同一仓库可能有多条记录）
    matched = 0
    auto_created = 0
    auto_created_skus: List[Dict] = []
    skipped_no_sku = 0
    skipped_warehouse = 0

    # records: {warehouse: {product_id_str: {available, reserved, inbound}}}
    records: Dict[str, Dict[str, Dict[str, int]]] = {}

    for item in stocks_data:
        spec_no = item.get("spec_no")  # 商家编码 = SKU
        if not spec_no:
            skipped_no_sku += 1
            continue
        spec_no = str(spec_no).strip()

        warehouse_name = str(item.get("warehouse_name", "默认仓库")).strip() or "默认仓库"

        # 仓库白名单过滤：只同步核心仓库
        if warehouse_name not in WAREHOUSE_WHITELIST:
            skipped_warehouse += 1
            continue

        # 匹配或自动创建 Product
        product_id = sku_to_id.get(spec_no)
        if not product_id:
            goods_name = str(item.get("goods_name", spec_no)).strip()
            spec_name = str(item.get("spec_name", "")).strip()
            product_name = f"{goods_name} {spec_name}".strip() if spec_name else goods_name
            brand_name = str(item.get("brand_name", "")).strip()

            new_product = Product(
                sku=spec_no,
                product_name=product_name or spec_no,
                brand=_normalize_brand(brand_name),
                category="商品",
                status="active",
            )
            db.add(new_product)
            db.flush()
            product_id = new_product.id
            sku_to_id[spec_no] = product_id
            auto_created += 1
            auto_created_skus.append({"sku": spec_no, "name": (product_name or spec_no)[:50]})

        matched += 1
        pid_str = str(product_id)

        # 解析库存数量
        def _safe_int(val) -> int:
            try:
                return int(float(val)) if val is not None else 0
            except (TypeError, ValueError):
                return 0

        stock_num = _safe_int(item.get("stock_num"))       # 库存量（实物）
        lock_num = _safe_int(item.get("lock_num"))          # 锁定量
        unpay_num = _safe_int(item.get("unpay_num"))        # 未付款量
        order_num = _safe_int(item.get("order_num"))        # 待审核量
        sending_num = _safe_int(item.get("sending_num"))    # 待发货量
        purchase_num = _safe_int(item.get("purchase_num"))  # 采在途量
        transfer_num = _safe_int(item.get("transfer_num"))  # 调拨在途量

        available = stock_num
        reserved = lock_num + unpay_num + order_num + sending_num
        inbound = purchase_num + transfer_num

        # 聚合（同SKU同仓库可能有多条记录）
        if warehouse_name not in records:
            records[warehouse_name] = {}
        if pid_str not in records[warehouse_name]:
            records[warehouse_name][pid_str] = {"available": 0, "reserved": 0, "inbound": 0}

        records[warehouse_name][pid_str]["available"] += available
        records[warehouse_name][pid_str]["reserved"] += reserved
        records[warehouse_name][pid_str]["inbound"] += inbound

    # ===== 原地 upsert：按 (product_id, warehouse) 更新，不按 date 创建新记录 =====
    # 每次 sync 找到现有记录就更新数量 + date=today，避免跨天累积重复
    inserted = 0
    updated = 0
    unchanged = 0

    for warehouse, pid_map in records.items():
        if not pid_map:
            continue
        product_ids = list(pid_map.keys())

        # 查找该仓库下所有已有记录（不限 date），按 product_id 分组
        existing_records = (
            db.query(Inventory)
            .filter(
                Inventory.warehouse == warehouse,
                Inventory.product_id.in_(product_ids),
            )
            .all()
        )
        existing_map = {str(r.product_id): r for r in existing_records}

        for pid_str, qty in pid_map.items():
            existing = existing_map.get(pid_str)
            if existing:
                changed = False
                if existing.available_qty != qty["available"]:
                    existing.available_qty = qty["available"]
                    changed = True
                if existing.reserved_qty != qty["reserved"]:
                    existing.reserved_qty = qty["reserved"]
                    changed = True
                if existing.inbound_qty != qty["inbound"]:
                    existing.inbound_qty = qty["inbound"]
                    changed = True
                # 每次同步都更新 date 到今天
                existing.date = sync_date
                existing.updated_at = datetime.now()
                if changed:
                    updated += 1
                else:
                    unchanged += 1
            else:
                new_inv = Inventory(
                    product_id=pid_str,
                    warehouse=warehouse,
                    available_qty=qty["available"],
                    reserved_qty=qty["reserved"],
                    inbound_qty=qty["inbound"],
                    date=sync_date,
                )
                db.add(new_inv)
                inserted += 1

    db.commit()

    # 记录同步元数据
    warehouse_list = list(records.keys())
    meta = {
        "last_sync_at": datetime.now().isoformat(),
        "synced_date": sync_date.isoformat(),
        "total_from_api": len(stocks_data),
        "api_total_count": total_count,
        "matched_count": matched,
        "auto_created": auto_created,
        "auto_created_skus": auto_created_skus[:30],
        "skipped_no_sku": skipped_no_sku,
        "skipped_warehouse": skipped_warehouse,
        "inserted": inserted,
        "updated": updated,
        "unchanged": unchanged,
        "warehouses": warehouse_list,
        "warehouse_count": len(warehouse_list),
        "data_source": "wangdian_api",
        "api_params": {
            "start_time": start_time,
            "end_time": end_time,
        },
    }
    _write_sync_meta(meta)

    msg_parts = [
        f"旺店通API同步成功",
        f"拉取 {len(stocks_data)} 条库存记录",
        f"匹配 {matched} 个 SKU",
    ]
    if auto_created > 0:
        msg_parts.append(f"自动创建 {auto_created} 个新品")
    msg_parts.append(f"新增 {inserted} 条 / 更新 {updated} 条 / 未变 {unchanged} 条")
    if skipped_warehouse > 0:
        msg_parts.append(f"过滤 {skipped_warehouse} 条非核心仓库记录")
    msg_parts.append(f"覆盖 {len(warehouse_list)} 个仓库: {', '.join(warehouse_list)}")

    return {
        "status": "success",
        "message": "，".join(msg_parts),
        "synced_date": sync_date.isoformat(),
        "total_from_api": len(stocks_data),
        "matched_count": matched,
        "auto_created": auto_created,
        "auto_created_skus": auto_created_skus[:30],
        "inserted": inserted,
        "updated": updated,
        "unchanged": unchanged,
        "skipped_warehouse": skipped_warehouse,
        "warehouse_count": len(warehouse_list),
        "warehouses": warehouse_list,
        "last_sync_at": meta["last_sync_at"],
    }


def get_wangdian_sync_status(db: Session) -> Dict:
    """查询旺店通同步状态（只读，不触发同步）."""
    meta = _read_sync_meta()

    # sales-analysis inventory 表最新日期
    sa_latest = db.query(func.max(Inventory.date)).scalar()

    # 检查是否配置了旺店通凭证
    from app.core.config import settings
    configured = bool(getattr(settings, "WANGDIAN_SID", "") and getattr(settings, "WANGDIAN_APPKEY", "") and getattr(settings, "WANGDIAN_APPSECRET", ""))

    return {
        "configured": configured,
        "within_allowed_time": True,
        "allowed_time_window": "无限制（stock_query.php）",
        "last_sync_at": meta.get("last_sync_at"),
        "last_synced_date": meta.get("synced_date"),
        "last_total_from_api": meta.get("total_from_api"),
        "last_matched": meta.get("matched_count"),
        "last_auto_created": meta.get("auto_created"),
        "last_inserted": meta.get("inserted"),
        "last_updated": meta.get("updated"),
        "last_warehouses": meta.get("warehouses", []),
        "last_warehouse_count": meta.get("warehouse_count", 0),
        "sales_analysis_latest_date": sa_latest.isoformat() if sa_latest else None,
        "data_source": meta.get("data_source", "wangdian_api"),
    }
