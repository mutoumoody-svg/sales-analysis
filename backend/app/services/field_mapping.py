"""
旺店通字段映射配置 v2
====================
适配新数据结构（2026-07起统一格式）：

1. 销售出库明细表 (94 columns, Sheet1)
   - 包含真实成本/毛利数据
   - 最后一行为"合计:"行，需过滤
   - 无退货Sheet（退货数据在汇总表中）

2. 货品销售汇总表 (23 columns, Sheet1)
   - 按店铺×货品维度汇总
   - 包含发货/退货/实际销售的数量、金额、成本、利润

3. 库存文件 (多Sheet结构, 保持不变)
"""

import re
from typing import Optional


# ============================================
# 平台识别规则 - 从店铺名称提取平台
# ============================================
PLATFORM_PATTERNS = [
    (r"天猫|淘宝|猫超", "天猫"),
    (r"京东", "京东"),
    (r"抖音|抖店", "抖音"),
    (r"拼多多", "拼多多"),
    (r"微信|微店|视频号", "微信"),
    (r"小红书", "小红书"),
    (r"快手", "快手"),
    (r"1688|阿里巴巴", "1688"),
    (r"得物", "得物"),
    (r"网易严选", "网易严选"),
    (r"叮咚", "叮咚"),
    (r"稻壳", "稻壳"),
]


def extract_platform(store_name: str) -> str:
    """从店铺名称中提取平台信息。"""
    if not store_name or not isinstance(store_name, str):
        return "未知"
    for pattern, platform in PLATFORM_PATTERNS:
        if re.search(pattern, store_name):
            return platform
    return "其他"


# ============================================
# 销售类型映射 - 旺店通订单类型 → 系统销售类型
# ============================================
SALES_TYPE_MAPPING = {
    "网店销售": "Retail",
    "线下零售": "Retail",
    "售后换货": "Exchange",
    "订单补发": "Reship",
    "网店换货": "Exchange",
    "批发": "Wholesale",
    "批发销售": "Wholesale",
    "直播": "Retail",
    "内购": "Promotion",
    "赠品": "Sample",
    "清仓": "Clearance",
    "其他": "Retail",
}

DEFAULT_SALES_TYPE = "Retail"


def map_sales_type(wdt_type: str) -> str:
    """将旺店通订单类型映射到系统销售类型。"""
    if not wdt_type or not isinstance(wdt_type, str):
        return DEFAULT_SALES_TYPE
    return SALES_TYPE_MAPPING.get(wdt_type.strip(), DEFAULT_SALES_TYPE)


# ============================================
# 合计行过滤 - 旺店通导出末尾的"合计:"行
# ============================================
TOTAL_ROW_MARKERS = {"合计:", "合计", "总计", "小计"}


def is_total_row(row_dict: dict) -> bool:
    """检测是否为旺店通导出的合计行。"""
    order_no = str(row_dict.get("订单编号", "")).strip()
    if order_no in TOTAL_ROW_MARKERS:
        return True
    # 商家编码和店铺同时为空也是合计行
    sku = row_dict.get("商家编码")
    store = row_dict.get("店铺")
    if (sku is None or (isinstance(sku, float) and str(sku) == "nan")) and \
       (store is None or (isinstance(store, float) and str(store) == "nan")):
        return True
    return False


# ============================================
# 数据转换工具函数
# ============================================
def parse_decimal(value, default=0):
    """安全解析数值，处理 '无权限' 等非数值文本。"""
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return value
    s = str(value).strip()
    if s in ("", "无权限", "NaN", "nan", "None", "-"):
        return default
    try:
        return float(s)
    except (ValueError, TypeError):
        return default


def parse_decimal_nullable(value):
    """解析数值，不可用时返回None（用于成本字段）。"""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return value
    s = str(value).strip()
    if s in ("", "无权限", "NaN", "nan", "None", "-"):
        return None
    try:
        return float(s)
    except (ValueError, TypeError):
        return None


def parse_int(value, default=0):
    """安全解析整数。"""
    val = parse_decimal(value, default)
    try:
        return int(val)
    except (ValueError, TypeError):
        return default


def parse_date(value):
    """解析日期，返回 YYYY-MM-DD 格式字符串。"""
    if value is None:
        return None
    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m-%d")
    s = str(value).strip()
    if s in ("", "NaT", "NaN", "nan", "None"):
        return None
    m = re.match(r"(\d{4}[-/]\d{1,2}[-/]\d{1,2})", s)
    if m:
        return m.group(1).replace("/", "-")
    return None


def get_customer_name(row_dict: dict) -> Optional[str]:
    """从行数据中获取客户名称，优先客户网名，回退收件人。"""
    name = row_dict.get("客户网名")
    if name and str(name).strip() and str(name).strip() not in ("NaN", "nan", "None"):
        return str(name).strip()
    name = row_dict.get("收件人")
    if name and str(name).strip() and str(name).strip() not in ("NaN", "nan", "None"):
        return str(name).strip()
    return None


# ============================================
# 库存文件字段映射（保持不变）
# ============================================
INVENTORY_SHEET_CATEGORIES = {
    "01_商品-STTOKE": "STTOKE",
    "02_商品-慕咖": "慕咖",
    "03_商品-食品": "食品",
    "04_商品-周边商品": "周边商品",
    "05_包装物料-STTOKE": "包装物料-STTOKE",
    "06_包装物料-慕咖": "包装物料-慕咖",
    "07_包装物料-食品": "包装物料-食品",
    "08_包装物料-未分类": "包装物料-未分类",
}

INVENTORY_WAREHOUSE_COLUMNS = [
    "美乐印刷",
    "速易正品仓",
    "速易瑞福兰仓",
]
