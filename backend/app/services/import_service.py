"""
数据导入服务 v2
================
适配新旺店通数据结构（2026-07起统一格式）。

支持三种导入：
1. import_sales_detail()  - 销售出库明细表导入（94列，含成本/毛利，合计行过滤）
2. import_sales_summary() - 货品销售汇总表导入（23列，店铺×货品维度）
3. import_inventory()     - 库存文件导入（多Sheet，保持不变）

核心改进：
- 合计行自动过滤（订单编号="合计:" 或 商家编码为空）
- 成本/毛利数据写入 OrderItem + Order
- 批量 flush 优化（每500行flush一次，32K行不超时）
- 汇总表 upsert 模式（同店铺×商品覆盖更新）
"""

import math
import os
from datetime import datetime, date
from typing import Optional

import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.store import Store
from app.models.product import Product
from app.models.customer import Customer
from app.models.order import Order, OrderItem
from app.models.inventory import Inventory
from app.models.sales_summary import SalesSummary
from app.services import field_mapping as fm
from app.services.system_cost_service import recalc_orders_gross_profit
from sqlalchemy import delete


class ImportResult:
    """导入结果摘要。"""

    def __init__(self, import_type: str):
        self.import_type = import_type
        self.total_rows = 0
        self.processed = 0
        self.skipped = 0
        self.filtered_total_rows = 0
        self.errors = []
        self.stores_created = 0
        self.products_created = 0
        self.customers_created = 0
        self.orders_created = 0
        self.order_items_created = 0
        self.inventory_records = 0
        self.summary_records = 0
        self.started_at = datetime.now()
        self.finished_at: Optional[datetime] = None

    def finish(self):
        self.finished_at = datetime.now()

    def to_dict(self) -> dict:
        return {
            "import_type": self.import_type,
            "total_rows": self.total_rows,
            "processed": self.processed,
            "skipped": self.skipped,
            "filtered_total_rows": self.filtered_total_rows,
            "errors": self.errors[:20],
            "error_count": len(self.errors),
            "stores_created": self.stores_created,
            "products_created": self.products_created,
            "customers_created": self.customers_created,
            "orders_created": self.orders_created,
            "order_items_created": self.order_items_created,
            "inventory_records": self.inventory_records,
            "summary_records": self.summary_records,
            "started_at": self.started_at.isoformat(),
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "duration_seconds": round((self.finished_at - self.started_at).total_seconds(), 2) if self.finished_at else None,
        }

    def __str__(self):
        d = self.to_dict()
        lines = [
            f"=== Import Result: {d['import_type']} ===",
            f"  Rows: {d['total_rows']} total, {d['processed']} processed, {d['skipped']} skipped, {d['filtered_total_rows']} total-rows-filtered",
            f"  Created: stores={d['stores_created']}, products={d['products_created']}, customers={d['customers_created']}",
            f"  Orders: {d['orders_created']} orders, {d['order_items_created']} items",
            f"  Summary: {d['summary_records']} records",
            f"  Inventory: {d['inventory_records']} records",
            f"  Errors: {d['error_count']}",
            f"  Duration: {d['duration_seconds']}s",
        ]
        return "\n".join(lines)


# ============================================
# get_or_create 工具函数（带缓存）
# ============================================
def get_or_create_store(db: Session, store_name: str, result: ImportResult, cache: dict = None) -> Optional[Store]:
    """获取或创建店铺（带缓存）。"""
    if not store_name or not str(store_name).strip():
        return None
    store_name = str(store_name).strip()

    if cache is not None and store_name in cache:
        return cache[store_name]

    stmt = select(Store).where(Store.store_name == store_name)
    store = db.execute(stmt).scalar_one_or_none()
    if not store:
        platform = fm.extract_platform(store_name)
        store = Store(store_name=store_name, platform=platform)
        db.add(store)
        db.flush()
        result.stores_created += 1

    if cache is not None:
        cache[store_name] = store
    return store


def get_or_create_product(
    db: Session,
    sku: str,
    product_name: str,
    brand: str = None,
    category: str = None,
    result: ImportResult = None,
    cache: dict = None,
) -> Optional[Product]:
    """获取或创建商品（带缓存）。"""
    if not sku or not str(sku).strip():
        return None
    sku = str(sku).strip()

    if cache is not None and sku in cache:
        return cache[sku]

    stmt = select(Product).where(Product.sku == sku)
    product = db.execute(stmt).scalar_one_or_none()
    if not product:
        product = Product(
            sku=sku,
            product_name=str(product_name).strip() if product_name else sku,
            brand=str(brand).strip() if brand else None,
            category=str(category).strip() if category else None,
        )
        db.add(product)
        db.flush()
        if result:
            result.products_created += 1
    else:
        updated = False
        if brand and str(brand).strip() and not product.brand:
            product.brand = str(brand).strip()
            updated = True
        if category and str(category).strip() and not product.category:
            product.category = str(category).strip()
            updated = True
        if product_name and str(product_name).strip() and not product.product_name:
            product.product_name = str(product_name).strip()
            updated = True
        if updated:
            db.flush()

    if cache is not None:
        cache[sku] = product
    return product


def get_or_create_customer(
    db: Session, customer_name: str, result: ImportResult, cache: dict = None
) -> Optional[Customer]:
    """获取或创建客户（带缓存）。"""
    if not customer_name or not str(customer_name).strip():
        return None
    customer_name = str(customer_name).strip()

    if cache is not None and customer_name in cache:
        return cache[customer_name]

    stmt = select(Customer).where(Customer.customer_name == customer_name)
    customer = db.execute(stmt).scalar_one_or_none()
    if not customer:
        customer = Customer(customer_name=customer_name, customer_type="Normal")
        db.add(customer)
        db.flush()
        result.customers_created += 1

    if cache is not None:
        cache[customer_name] = customer
    return customer


# ============================================
# 销售出库明细导入
# ============================================
FLUSH_INTERVAL = 500  # 每500行flush一次


def import_sales_detail(
    db: Session, file_path: str, sheet_name: str = None, period: str = None
) -> ImportResult:
    """导入旺店通销售出库明细表。

    Args:
        db: 数据库会话
        file_path: Excel 文件路径
        sheet_name: Sheet名称，None则自动检测第一个Sheet
        period: 会计期间(YYYY-MM)，仅用于记录/显示，明细数据日期来自"下单时间"列

    Returns:
        ImportResult 导入结果摘要
    """
    result = ImportResult("sales_detail")

    # 自动检测sheet name：优先用指定的，否则用第一个sheet
    try:
        if sheet_name:
            df = pd.read_excel(file_path, sheet_name=sheet_name)
        else:
            # 不指定sheet_name时，自动读取第一个sheet
            xls = pd.ExcelFile(file_path)
            actual_sheet = xls.sheet_names[0] if xls.sheet_names else "Sheet1"
            df = pd.read_excel(file_path, sheet_name=actual_sheet)
    except Exception as e:
        # 如果指定sheet_name失败，尝试读取第一个sheet
        try:
            xls = pd.ExcelFile(file_path)
            actual_sheet = xls.sheet_names[0] if xls.sheet_names else "Sheet1"
            df = pd.read_excel(file_path, sheet_name=actual_sheet)
        except Exception as e2:
            result.errors.append(f"文件读取失败: {e2}")
            result.finish()
            return result

    result.total_rows = len(df)

    required_cols = ["订单编号", "店铺", "商家编码", "货品名称"]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        result.errors.append(f"缺少必需列: {missing}")
        result.finish()
        return result

    # 缓存字典：减少数据库查询
    store_cache = {}
    product_cache = {}
    customer_cache = {}
    order_cache = {}  # order_no -> Order object
    cleared_orders = set()  # 已清除旧明细的订单号集合

    for idx, row in df.iterrows():
        try:
            row_dict = row.to_dict()

            # 过滤合计行
            if fm.is_total_row(row_dict):
                result.filtered_total_rows += 1
                continue

            order_no = str(row_dict.get("订单编号", "")).strip()
            if not order_no or order_no in ("NaN", "nan", "None"):
                result.skipped += 1
                continue

            # 获取或创建店铺
            store = get_or_create_store(db, row_dict.get("店铺"), result, store_cache)
            if not store:
                result.errors.append(f"行 {idx+2}: 店铺为空")
                result.skipped += 1
                continue

            # 获取或创建商品
            product = get_or_create_product(
                db,
                sku=row_dict.get("商家编码"),
                product_name=row_dict.get("货品名称"),
                brand=row_dict.get("品牌"),
                category=row_dict.get("分类"),
                result=result,
                cache=product_cache,
            )
            if not product:
                result.errors.append(f"行 {idx+2}: SKU为空")
                result.skipped += 1
                continue

            # 获取或创建客户
            customer_name = fm.get_customer_name(row_dict)
            customer = None
            if customer_name:
                customer = get_or_create_customer(db, customer_name, result, customer_cache)

            # 获取或创建订单（支持重复导入：已存在则更新）
            if order_no not in order_cache:
                # 先查数据库，避免重复导入时唯一约束冲突
                existing_order = db.execute(
                    select(Order).where(Order.order_no == order_no)
                ).scalar_one_or_none()

                if existing_order:
                    # 订单已存在，更新字段
                    order_date = fm.parse_date(row_dict.get("下单时间"))
                    if order_date:
                        existing_order.order_date = order_date
                    existing_order.sales_type = fm.map_sales_type(row_dict.get("订单类型"))
                    existing_order.total_amount = fm.parse_decimal(row_dict.get("订单支付金额"), 0)
                    existing_order.discount = fm.parse_decimal(row_dict.get("订单总优惠"), 0)
                    existing_order.shipping_fee = fm.parse_decimal(row_dict.get("邮费"), 0)
                    existing_order.shipping_cost = fm.parse_decimal(row_dict.get("邮资成本"), 0)
                    existing_order.packaging_cost = fm.parse_decimal(row_dict.get("订单包装成本"), 0)
                    gp = fm.parse_decimal_nullable(row_dict.get("订单毛利"))
                    if gp is not None:
                        existing_order.gross_profit = gp
                    gpr = fm.parse_decimal_nullable(row_dict.get("毛利率"))
                    if gpr is not None:
                        existing_order.gross_profit_rate = gpr
                    # 首次遇到已存在订单时，清除旧明细，避免重复导入产生重复行
                    if order_no not in cleared_orders:
                        db.execute(delete(OrderItem).where(OrderItem.order_id == existing_order.id))
                        cleared_orders.add(order_no)
                    order_cache[order_no] = existing_order
                    order = existing_order
                else:
                    order_date = fm.parse_date(row_dict.get("下单时间"))
                    if not order_date:
                        order_date = date.today().isoformat()

                    sales_type = fm.map_sales_type(row_dict.get("订单类型"))
                    total_amount = fm.parse_decimal(row_dict.get("订单支付金额"), 0)
                    discount = fm.parse_decimal(row_dict.get("订单总优惠"), 0)
                    shipping_fee = fm.parse_decimal(row_dict.get("邮费"), 0)
                    shipping_cost = fm.parse_decimal(row_dict.get("邮资成本"), 0)
                    packaging_cost = fm.parse_decimal(row_dict.get("订单包装成本"), 0)
                    gross_profit = fm.parse_decimal_nullable(row_dict.get("订单毛利"))
                    gross_profit_rate = fm.parse_decimal_nullable(row_dict.get("毛利率"))

                    order = Order(
                        order_no=order_no,
                        order_date=order_date,
                        store_id=store.id,
                        customer_id=customer.id if customer else None,
                        sales_type=sales_type,
                        total_amount=total_amount,
                        discount=discount,
                        shipping_fee=shipping_fee,
                        shipping_cost=shipping_cost,
                        packaging_cost=packaging_cost,
                        gross_profit=gross_profit,
                        gross_profit_rate=gross_profit_rate,
                    )
                    db.add(order)
                    db.flush()
                    order_cache[order_no] = order
                    result.orders_created += 1
            else:
                order = order_cache[order_no]

            # 创建订单明细
            quantity = fm.parse_int(row_dict.get("货品数量"), 0)
            if quantity == 0:
                # 数量为0的赠品行仍然记录
                pass

            selling_price = fm.parse_decimal(row_dict.get("货品成交价"), 0)
            amount = fm.parse_decimal(row_dict.get("货品成交总价"), 0)
            if amount == 0 and selling_price > 0:
                amount = selling_price * quantity

            unit_cost = fm.parse_decimal_nullable(row_dict.get("货品成本"))
            total_cost = fm.parse_decimal_nullable(row_dict.get("货品总成本"))
            # 系统成本优先：有系统成本时覆盖旺店通成本
            if product.unit_cost is not None and product.unit_cost > 0:
                unit_cost = product.unit_cost
                total_cost = round(product.unit_cost * quantity, 2)
            warehouse = row_dict.get("仓库")
            warehouse = str(warehouse).strip() if warehouse and str(warehouse).strip() not in ("NaN", "nan", "None") else None

            item = OrderItem(
                order_id=order.id,
                product_id=product.id,
                quantity=quantity,
                selling_price=selling_price,
                amount=amount,
                unit_cost=unit_cost,
                total_cost=total_cost,
                warehouse=warehouse,
            )
            db.add(item)
            result.order_items_created += 1
            result.processed += 1

            # 批量flush优化
            if result.processed % FLUSH_INTERVAL == 0:
                db.flush()

        except Exception as e:
            result.errors.append(f"行 {idx+2}: {str(e)[:100]}")
            result.skipped += 1
            continue

    # 系统成本优先：用系统成本重算本次导入订单的毛利
    # （订单毛利 = total_amount - Σ明细系统成本，明细缺成本的订单保留导入原值）
    recalc_orders_gross_profit(db, [o.id for o in order_cache.values()])

    db.commit()
    result.finish()
    return result


# ============================================
# 货品销售汇总表导入
# ============================================
def import_sales_summary(
    db: Session, file_path: str, sheet_name: str = "Sheet1", period: str = None
) -> ImportResult:
    """导入旺店通货品销售汇总表。

    按店铺×货品维度汇总，包含发货/退货/实际销售的数量、金额、成本、利润。
    使用 upsert 模式：同店铺×商品×月份已存在则更新。

    Args:
        db: 数据库会话
        file_path: Excel 文件路径
        sheet_name: Sheet名称，默认 'Sheet1'
        period: 会计期间 (YYYY-MM)，默认自动推断（文件名中的年月或当前月）

    Returns:
        ImportResult 导入结果摘要
    """
    result = ImportResult("sales_summary")

    # 推断 period：优先用传入参数，其次从文件名提取，最后用当前月
    if not period:
        import re
        fname = os.path.basename(file_path)
        # 先匹配完整格式 2026-07 或 2026_07
        m = re.search(r'(20\d{2})[-_]?(0[1-9]|1[0-2])', fname)
        if m:
            period = f"{m.group(1)}-{m.group(2)}"
        else:
            # 再匹配简写格式 2607 (2位年+2位月)
            m = re.search(r'(?:^|[^0-9])(\d{2})(0[1-9]|1[0-2])(?:[^0-9]|$)', fname)
            if m:
                period = f"20{m.group(1)}-{m.group(2)}"
            else:
                period = date.today().strftime("%Y-%m")

    try:
        df = pd.read_excel(file_path, sheet_name=sheet_name)
    except Exception as e:
        result.errors.append(f"文件读取失败: {e}")
        result.finish()
        return result

    result.total_rows = len(df)

    required_cols = ["店铺", "货品编号", "货品名称"]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        result.errors.append(f"缺少必需列: {missing}")
        result.finish()
        return result

    store_cache = {}
    product_cache = {}
    summary_cache = {}

    for idx, row in df.iterrows():
        try:
            row_dict = row.to_dict()

            # 过滤合计行和空货品行
            store_name = str(row_dict.get("店铺", "")).strip()
            sku = str(row_dict.get("货品编号", "")).strip()
            if not store_name or store_name in ("合计:", "合计", "NaN", "nan", "None"):
                result.skipped += 1
                continue
            if not sku or sku in ("NaN", "nan", "None"):
                result.skipped += 1
                continue

            # 获取或创建店铺
            store = get_or_create_store(db, store_name, result, store_cache)
            if not store:
                result.skipped += 1
                continue

            # 获取或创建商品
            product = get_or_create_product(
                db,
                sku=sku,
                product_name=row_dict.get("货品名称"),
                brand=row_dict.get("品牌"),
                category=row_dict.get("分类"),
                result=result,
                cache=product_cache,
            )
            if not product:
                result.skipped += 1
                continue

            # 检查是否已存在（upsert: store_id + product_id + period）
            summary_key = (store.id, product.id, period)
            duplicate_in_file = summary_key in summary_cache
            if duplicate_in_file:
                existing = summary_cache[summary_key]
            else:
                stmt = select(SalesSummary).where(
                    SalesSummary.store_id == store.id,
                    SalesSummary.product_id == product.id,
                    SalesSummary.period == period,
                )
                existing = db.execute(stmt).scalar_one_or_none()

            # 解析所有字段
            data = {
                "ship_qty": fm.parse_int(row_dict.get("发货总量"), 0),
                "return_qty": fm.parse_int(row_dict.get("退货总量"), 0),
                "net_qty": fm.parse_int(row_dict.get("实际销售量"), 0),
                "unshipped_refund_qty": fm.parse_int(row_dict.get("未发货退款数量"), 0),
                "gift_qty": fm.parse_int(row_dict.get("赠品数量"), 0),
                "avg_price": fm.parse_decimal_nullable(row_dict.get("均价")),
                "ship_amount": fm.parse_decimal(row_dict.get("发货总金额"), 0),
                "return_amount": fm.parse_decimal(row_dict.get("退货总金额"), 0),
                "net_amount": fm.parse_decimal(row_dict.get("实际销售额"), 0),
                "unshipped_refund_amount": fm.parse_decimal(row_dict.get("未发货退款金额"), 0),
                "total_cost": fm.parse_decimal(row_dict.get("货品总成本"), 0),
                "return_cost": fm.parse_decimal(row_dict.get("退货总成本"), 0),
                "net_cost": fm.parse_decimal(row_dict.get("实际总成本"), 0),
                "commission_cost": fm.parse_decimal(row_dict.get("佣金成本"), 0),
                "unknown_cost_sales": fm.parse_decimal(row_dict.get("未知成本销售总额"), 0),
                "ship_profit": fm.parse_decimal(row_dict.get("货品总利润"), 0),
                "net_profit": fm.parse_decimal(row_dict.get("实际总利润"), 0),
            }

            # 系统成本优先：有系统成本时用系统成本覆盖旺店通成本/利润
            if product.unit_cost is not None and product.unit_cost > 0:
                # SQLAlchemy Numeric returns Decimal while imported Excel amounts
                # are floats. Normalize to float before arithmetic.
                uc = float(product.unit_cost)
                data["total_cost"] = round(uc * data["ship_qty"], 2)
                data["return_cost"] = round(uc * data["return_qty"], 2)
                data["net_cost"] = round(uc * data["net_qty"], 2)
                data["ship_profit"] = round(data["ship_amount"] - data["total_cost"], 2)
                data["net_profit"] = round(data["net_amount"] - data["net_cost"], 2)

            if existing and duplicate_in_file:
                additive_fields = [
                    "ship_qty", "return_qty", "net_qty", "unshipped_refund_qty", "gift_qty",
                    "ship_amount", "return_amount", "net_amount", "unshipped_refund_amount",
                    "total_cost", "return_cost", "net_cost", "commission_cost",
                    "unknown_cost_sales", "ship_profit", "net_profit",
                ]
                for field in additive_fields:
                    setattr(existing, field, (getattr(existing, field) or 0) + (data[field] or 0))
                existing.avg_price = (
                    existing.net_amount / existing.net_qty if existing.net_qty else None
                )
            elif existing:
                # 更新已有记录
                for k, v in data.items():
                    setattr(existing, k, v)
                result.summary_records += 1  # 更新也算一条记录
            else:
                # 创建新记录
                summary = SalesSummary(
                    store_id=store.id,
                    product_id=product.id,
                    period=period,
                    **data,
                )
                db.add(summary)
                existing = summary
                result.summary_records += 1

            summary_cache[summary_key] = existing

            result.processed += 1

            if result.processed % FLUSH_INTERVAL == 0:
                db.flush()

        except Exception as e:
            result.errors.append(f"行 {idx+2}: {str(e)[:100]}")
            result.skipped += 1
            continue

    db.commit()
    result.finish()
    return result


# ============================================
# 库存文件导入（保持不变）
# ============================================
def import_inventory(
    db: Session,
    file_path: str,
    snapshot_date: Optional[str] = None,
) -> ImportResult:
    """导入旺店通库存文件（多Sheet）。

    Args:
        db: 数据库会话
        file_path: Excel 文件路径
        snapshot_date: 库存快照日期，默认今天

    Returns:
        ImportResult 导入结果摘要
    """
    result = ImportResult("inventory")

    if not snapshot_date:
        snapshot_date = date.today().isoformat()

    try:
        xls = pd.ExcelFile(file_path)
    except Exception as e:
        result.errors.append(f"文件读取失败: {e}")
        result.finish()
        return result

    product_cache = {}

    for sheet_name in xls.sheet_names:
        if "预警" in sheet_name:
            continue

        try:
            df = pd.read_excel(file_path, sheet_name=sheet_name)
        except Exception as e:
            result.errors.append(f"Sheet [{sheet_name}] 读取失败: {e}")
            continue

        result.total_rows += len(df)

        if "货品编号" not in df.columns:
            result.errors.append(f"Sheet [{sheet_name}]: 缺少'货品编号'列")
            continue

        for idx, row in df.iterrows():
            try:
                row_dict = row.to_dict()

                sku = str(row_dict.get("货品编号", "")).strip()
                if not sku or sku in ("NaN", "nan", "None"):
                    result.skipped += 1
                    continue

                product = get_or_create_product(
                    db,
                    sku=sku,
                    product_name=row_dict.get("货品名称"),
                    result=result,
                    cache=product_cache,
                )
                if not product:
                    result.skipped += 1
                    continue

                for wh_name in fm.INVENTORY_WAREHOUSE_COLUMNS:
                    if wh_name not in row_dict:
                        continue
                    qty = fm.parse_int(row_dict.get(wh_name), 0)
                    if qty == 0:
                        continue

                    inv = Inventory(
                        product_id=product.id,
                        warehouse=wh_name,
                        available_qty=qty,
                        reserved_qty=0,
                        inbound_qty=0,
                        date=snapshot_date,
                    )
                    db.add(inv)
                    result.inventory_records += 1

                result.processed += 1

            except Exception as e:
                result.errors.append(f"Sheet [{sheet_name}] 行 {idx+2}: {str(e)[:80]}")
                result.skipped += 1
                continue

    db.commit()
    result.finish()
    return result


# ============================================
# 批量导入入口
# ============================================
def import_all(
    db: Session,
    detail_file: Optional[str] = None,
    summary_file: Optional[str] = None,
    inventory_file: Optional[str] = None,
    period: Optional[str] = None,
) -> dict:
    """批量导入所有数据源。

    Args:
        detail_file: 销售出库明细表文件路径
        summary_file: 货品销售汇总表文件路径
        inventory_file: 库存文件路径
        period: 会计期间 (YYYY-MM)，用于汇总表

    Returns:
        dict: 包含各数据源的导入结果
    """
    results = {}

    if detail_file:
        results["detail"] = import_sales_detail(db, detail_file, period=period).to_dict()

    if summary_file:
        results["summary"] = import_sales_summary(db, summary_file, period=period).to_dict()

    if inventory_file:
        results["inventory"] = import_inventory(db, inventory_file).to_dict()

    return results
