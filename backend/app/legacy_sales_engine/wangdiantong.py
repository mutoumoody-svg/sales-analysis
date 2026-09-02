"""
platforms/wangdiantong.py
旺店通数据读取 & 拆分（支持两种导出格式）

格式一：货品销售汇总表
  - 按时间段聚合，每行一个 SKU，无订单号
  - 字段：货品编号、货品名称、实际销售量、实际销售额、发货总金额、分类、店铺

格式二：原始订单导出 / 销售出库明细
  - 每行一笔订单内的一个 SKU，有完整订单号与交易时间
  - 原始订单字段：订单编号、货品编号、货品名称、下单数量、单品支付金额 …
  - 出库明细字段：出库单编号、货品编号、货品名称、货品数量、货品成交总价 …

字段优先级（格式二）：
  - 数量：货品数量 → 下单数量
  - 销售额：货品成交总价 → 单品支付金额
  - 订单号：出库单编号 → 订单编号

自动识别：含 "订单编号" 或 "出库单编号" 列 → 原始订单/出库明细格式；否则 → 汇总表格式。
"""

import re
import pandas as pd

# ── 旺店通店铺名 → (仪表盘标准名, 平台) ──────────────────────────
# 同时兼容「汇总表」和「原始订单导出」两种命名方式
STORE_MAP: dict[str, tuple[str, str]] = {
    # 汇总表格式
    "天猫-慕咖官方旗舰店":           ("慕咖天猫旗舰店",            "天猫"),
    "京东-慕咖官方旗舰店":           ("慕咖京东旗舰店",            "京东"),
    "抖音-慕咖官方旗舰店":           ("慕咖抖音旗舰店",            "抖音"),
    "小红书-慕咖官方旗舰店":         ("慕咖小红书旗舰店",          "小红书"),
    "天猫-巴恩天然旗舰店":           ("巴恩天然天猫旗舰店",        "天猫"),
    "抖音-巴恩天然滋补旗舰店":       ("巴恩天然抖音旗舰店",        "抖音"),
    "小红书-巴恩天然官方旗舰店":     ("巴恩天然小红书旗舰店",      "小红书"),
    "康蜜乐食品天猫旗舰店":          ("康蜜乐天猫旗舰店",          "天猫"),
    "天猫-moodycoffee官方旗舰店":    ("慕咖MoodyCoffee天猫旗舰店", "天猫"),
    # 原始订单导出格式（不同命名）
    "慕咖天猫旗舰店":                ("慕咖天猫旗舰店",            "天猫"),
    "iSTTOKE京东店铺":               ("慕咖京东旗舰店",            "京东"),
    "小红书-慕咖旗舰店Moody":        ("慕咖小红书旗舰店",          "小红书"),
    "小红书巴恩天然旗舰店":          ("巴恩天然小红书旗舰店",      "小红书"),
    "京东-巴恩天然旗舰店":           ("巴恩天然京东旗舰店",        "京东"),
    "京东-巴恩天然POP旗舰店":        ("巴恩天然京东POP旗舰店",     "京东"),
    "moodycoffee":                   ("moodycoffee",               "天猫"),
}

# 跳过的店铺（非正式零售渠道）
SKIP_STORES = {
    "分销业务", "推广样品店铺",
    "小红书-稻壳店", "抖音-稻壳巴恩天然蜂蜜专卖店",
    "拼多多默认店铺YeAY", "微信视频号-巴恩天然旗舰店",
    "微信小店-康蜜乐", "小红书-可赞美食的店",
    "稻壳小红书",
}

# 仅分析这四个平台，其他渠道（得物/网易严选/分销/个人）一律排除
SUPPORTED_PLATFORMS = {"天猫", "京东", "小红书", "抖音"}

# 强制归类为赠品的 SKU（无论 WDT 数据中如何标记，一律清零收入）
_FORCE_GIFT_SKUS = {
    "BNMS",   # 巴恩天然蜂蜜木勺（随单赠品，不单独售卖）
}

# 原始订单导出中视为「已关闭」的订单状态
EXCLUDE_STATUS = {"已取消", "取消", "已关闭"}


# ─────────────────────────────────────────────────────────────────
# 通用工具
# ─────────────────────────────────────────────────────────────────

def _safe_str(val) -> str:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return ""
    return str(val).strip()


def _num_col(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series.apply(_safe_str), errors="coerce").fillna(0)


# 旺店通文件中期待出现的列名关键字（汇总表 + 原始订单 均涵盖）
_HEADER_KEYWORDS = {
    "货品编号", "货品名称", "实际销售量", "实际销售额", "发货总金额",
    "订单编号", "下单数量", "单品支付金额", "应收金额", "交易时间",
    "店铺", "分类",
    # 销售出库明细格式额外关键字
    "货品数量", "货品成交总价", "货品成交价", "付款时间", "出库单编号",
    # 货品销售汇总表退货列
    "总销量", "退货量", "退货总金额",
}

# 无表头格式（纯数据行）的位置列名映射
# 结构：货品编号 | 店铺 | 分类 | 货品名称 | 平均单价 | 总销量 | 退货量 | 实际销售量 | 实际销售额 | 发货总金额
_HEADERLESS_COL_MAP = {
    0: "货品编号",
    1: "店铺",
    2: "分类",
    3: "货品名称",
    4: "平均单价",
    5: "总销量",
    6: "退货量",
    7: "实际销售量",
    8: "实际销售额",
    9: "发货总金额",
}


def load_file(path: str) -> pd.DataFrame:
    """
    读取旺店通 Excel，自动检测真实列名所在行，跳过报表标题行。
    策略：
      1. 预读前 25 行，找命中关键字最多的行作为 header；
      2. 若没有任何命中（无表头格式），则用位置列名映射赋列名。
    """
    for eng in ["openpyxl", None]:
        try:
            kw = {"engine": eng} if eng else {}
            # ── 预读，找到真正的列名行 ────────────────────────────
            preview = pd.read_excel(path, header=None, nrows=25,
                                    dtype=str, **kw)
            best_row  = 0
            best_hits = 0
            for i, row in preview.iterrows():
                vals = {str(v).strip()
                        for v in row if pd.notna(v) and str(v).strip()}
                hits = len(vals & _HEADER_KEYWORDS)
                if hits > best_hits:
                    best_hits = hits
                    best_row  = i
            if best_hits >= 2:
                # ── 找到了明确的列名行 ────────────────────────────
                df = pd.read_excel(path, header=int(best_row), dtype=str, **kw)
                df.columns = df.columns.str.strip()
            else:
                # ── 无表头格式：全部行都是数据，按位置赋列名 ────
                df = pd.read_excel(path, header=None, dtype=str, **kw)
                rename = {i: name for i, name in _HEADERLESS_COL_MAP.items()
                          if i < len(df.columns)}
                df.rename(columns=rename, inplace=True)
            return df
        except Exception:
            continue
    raise ValueError(f"无法读取文件：{path}")


def detect_format(df: pd.DataFrame) -> str:
    """
    自动识别文件格式。
    返回 "orders"（原始订单 / 销售出库明细）或 "summary"（货品销售汇总表）。
    """
    if "订单编号" in df.columns or "出库单编号" in df.columns:
        return "orders"
    return "summary"


def _looks_like_order_id(s: str) -> bool:
    """判断字符串是否像订单号（纯数字且长度 > 10）。"""
    return len(s) > 10 and s.isdigit()


def list_recognized_stores(df: pd.DataFrame) -> list[tuple[str, str, str]]:
    """
    返回文件中可识别的店铺列表：
    [(原始名, 标准名, 平台), ...]

    防御性检查：若「店铺」列的值看起来全是订单号（纯数字长字符串），
    说明上传了错误的文件（如天猫后台导出），返回空列表避免爆炸式结果。
    """
    if "店铺" not in df.columns:
        return []
    unique_vals = [str(v).strip() for v in df["店铺"].dropna().unique()]
    # 若绝大多数"店铺"值看起来像订单号，视为文件格式错误
    order_id_count = sum(1 for v in unique_vals if _looks_like_order_id(v))
    if len(unique_vals) > 0 and order_id_count / len(unique_vals) > 0.5:
        return []   # 文件格式不对，忽略
    result = []
    for raw in unique_vals:
        if raw in SKIP_STORES:
            continue
        # 只处理明确在 STORE_MAP 中、且属于四大支持平台的店铺
        # 未登记的店铺（得物/网易严选/分销商/个人等）直接跳过
        if raw not in STORE_MAP:
            continue
        mapped, platform = STORE_MAP[raw]
        if platform not in SUPPORTED_PLATFORMS:
            continue
        result.append((raw, mapped, platform))
    return result


def extract_store_df(df: pd.DataFrame, store_raw: str) -> pd.DataFrame:
    """提取某个店铺的行数据。"""
    return df[df["店铺"].str.strip() == store_raw].copy().reset_index(drop=True)


# ─────────────────────────────────────────────────────────────────
# 格式一：货品销售汇总表
# ─────────────────────────────────────────────────────────────────

def to_standard_format(
    store_df: pd.DataFrame,
    period_date: str = "2026-02-01",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    将旺店通【货品销售汇总表】单店数据转换为标准 (orders_df, products_df)。

    period_date : 赋给"日期"列的时间戳字符串（无实际业务含义，仅用于月份归属）。
    """
    def _num(col):
        return pd.to_numeric(
            store_df.get(col, pd.Series([0] * len(store_df))),
            errors="coerce"
        ).fillna(0)

    # ── products_df ──────────────────────────────────────────────
    # 数量：优先 货品数量，回退 实际销售量
    qty_series = (
        _num("货品数量") if "货品数量" in store_df.columns
        else _num("实际销售量")
    )
    # 销售额：优先 货品成交总价，回退 实际销售额
    rev_series = (
        _num("货品成交总价") if "货品成交总价" in store_df.columns
        else _num("实际销售额")
    )
    products_df = pd.DataFrame({
        "日期":     period_date,
        "SKU编码":  store_df.get("货品编号",  pd.Series([""] * len(store_df))).apply(_safe_str).str.upper(),
        "商品名称": store_df.get("货品名称",  pd.Series([""] * len(store_df))).apply(_safe_str),
        "销量":     qty_series.astype(int),
        "商家收入": rev_series,
        "标价":     _num("发货总金额"),
        "是否赠品": store_df.apply(
            lambda row: "赠品" if (
                _safe_str(row.get("货品编号", "")).upper() in _FORCE_GIFT_SKUS
                or "赠品" in str(row.get("分类", ""))
            ) else "正品",
            axis=1,
        ),
    })
    # 过滤掉 SKU 为空或销量为 0 的行
    products_df = products_df[
        (products_df["SKU编码"] != "") & (products_df["销量"] > 0)
    ].reset_index(drop=True)

    # 强制赠品收入清零
    products_df.loc[
        products_df["SKU编码"].isin(_FORCE_GIFT_SKUS), "商家收入"
    ] = 0.0

    # 合成订单号（analyzer 需要 products_df 也有此列做 nunique）
    order_ids = [f"WDT-{i:04d}" for i in range(len(products_df))]
    products_df["主订单号"] = order_ids

    # ── orders_df（最简化，每个 SKU 行视作一笔聚合订单）────────
    orders_df = pd.DataFrame({
        "日期":      period_date,
        "主订单号":  order_ids,
        "订单状态":  "已完成",
        "商家收入":  products_df["商家收入"].values,
        "商品数量":  products_df["销量"].values,
        "SKU编码":   products_df["SKU编码"].values,
        "商品名称":  products_df["商品名称"].values,
    })

    return orders_df, products_df


# ─────────────────────────────────────────────────────────────────
# 格式二：原始订单导出
# ─────────────────────────────────────────────────────────────────

def _parse_region(region_raw: str):
    """
    '四川省 南充市 顺庆区' → ('四川省', '南充市')
    """
    parts = [p.strip() for p in _safe_str(region_raw).split() if p.strip()]
    province = parts[0] if len(parts) > 0 else ""
    city     = parts[1] if len(parts) > 1 else ""
    return province, city


def orders_to_standard_format(
    store_df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    将旺店通【原始订单导出】单店数据转换为标准 (orders_df, products_df)。

    收入字段说明：
      - products_df.商家收入 ← 单品支付金额（赠品为 0）
      - orders_df.商家收入   ← 应收金额（每笔订单取一次）
    """
    df = store_df.copy()

    # ── 过滤已取消订单（兼容出库明细：无订单状态列）────────────────
    status_col = next((c for c in ["订单状态", "出库单状态"] if c in df.columns), None)
    if status_col:
        before = len(df)
        df = df[~df[status_col].apply(_safe_str).isin(EXCLUDE_STATUS)].copy()
        if len(df) < before:
            print(f"  [WDT订单] 过滤取消订单 {before - len(df)} 条，剩余 {len(df)} 条")
    df["订单状态"] = df[status_col].apply(_safe_str) if status_col else "已完成"

    if df.empty:
        empty_o = pd.DataFrame(columns=["主订单号", "日期", "下单时间", "订单状态",
                                         "商家收入", "商品数量", "省", "市"])
        empty_p = pd.DataFrame(columns=["主订单号", "日期", "下单时间", "SKU编码",
                                         "商品名称", "是否赠品", "销量", "标价", "商家收入"])
        return empty_o, empty_p

    # ── 日期解析（兼容两种格式）─────────────────────────────────────
    # 统一以「发货时间」为准（与旺店通表格口径一致）；
    # 无发货时间时依次回退：交易时间 → 付款时间 → 下单时间
    time_col = next(
        (c for c in ["发货时间", "交易时间", "付款时间", "下单时间"] if c in df.columns), None
    )
    if time_col:
        df["_dt"] = pd.to_datetime(df[time_col].apply(_safe_str), errors="coerce")
    else:
        df["_dt"] = pd.NaT
    df["日期"] = df["_dt"].dt.date
    df["下单时间"] = df["_dt"].dt.strftime("%Y-%m-%d %H:%M:%S")

    # ── 赠品识别 ──────────────────────────────────────────────────
    # 优先级：强制赠品清单 > 赠品方式非空 > 货品名称含关键字
    gift_kws = ["赠品", "勿拍", "赠送"]
    def _is_gift(row):
        sku = _safe_str(row.get("货品编号", "")).upper()
        if sku in _FORCE_GIFT_SKUS:
            return True
        gift_way = _safe_str(row.get("赠品方式", ""))
        if gift_way:
            return True
        name = _safe_str(row.get("货品名称", ""))
        return any(k in name for k in gift_kws)

    df["是否赠品"] = df.apply(_is_gift, axis=1).map({True: "赠品", False: "正品"})

    # ── 订单号列（兼容两种导出）──────────────────────────────────────
    # 格式A（原始订单导出）：订单编号；格式B（销售出库明细）：出库单编号
    order_id_col = "订单编号" if "订单编号" in df.columns else "出库单编号"

    # ── 数值字段（货品数量 / 货品成交总价 优先）────────────────────
    # 数量：优先 货品数量，回退 下单数量
    qty_col      = "货品数量"     if "货品数量"     in df.columns else "下单数量"
    # 销售额：优先 货品成交总价，回退 单品支付金额
    unit_rev_col = "货品成交总价" if "货品成交总价" in df.columns else "单品支付金额"
    list_col     = "标价"         if "标价"         in df.columns else "货品原单价"

    df["_qty"]        = _num_col(df[qty_col])
    df["_unit_rev"]   = _num_col(df[unit_rev_col])   # per-SKU 收入（含赠品为0）
    df["_list_price"] = _num_col(df[list_col]) if list_col in df.columns else 0.0

    # 强制赠品收入清零（_FORCE_GIFT_SKUS 中的 SKU 无论原始数据如何，收入归零）
    df.loc[
        df["货品编号"].apply(_safe_str).str.upper().isin(_FORCE_GIFT_SKUS),
        "_unit_rev"
    ] = 0.0

    # 订单总收入：有应收金额列直接取；无则按订单/出库单汇总正品货品成交总价
    if "应收金额" in df.columns:
        df["_ord_rev"] = _num_col(df["应收金额"])
    else:
        unit_for_ord = df["_unit_rev"].where(df["是否赠品"] == "正品", 0)
        ord_sum = unit_for_ord.groupby(df[order_id_col].apply(_safe_str)).transform("sum")
        df["_ord_rev"] = ord_sum

    # ── 省市 ──────────────────────────────────────────────────────
    region_col  = "收货地区" if "收货地区" in df.columns else "收货地址"
    if region_col not in df.columns:
        df["收货地区"] = ""
        region_col = "收货地区"
    region_parsed   = df[region_col].apply(_parse_region)
    df["省"]         = region_parsed.apply(lambda x: x[0])
    df["市"]         = region_parsed.apply(lambda x: x[1])

    # ── SKU 编码规范化 ────────────────────────────────────────────
    df["SKU编码"] = df["货品编号"].apply(_safe_str).str.upper()

    # ── products_df ──────────────────────────────────────────────
    products_df = pd.DataFrame({
        "主订单号": df[order_id_col].apply(_safe_str),
        "日期":     df["日期"],
        "下单时间": df["下单时间"],
        "SKU编码":  df["SKU编码"],
        "商品名称": df["货品名称"].apply(_safe_str),
        "是否赠品": df["是否赠品"],
        "销量":     df["_qty"].astype(int),
        "标价":     df["_list_price"],
        "商家收入": df["_unit_rev"],   # 赠品为 0
        "订单状态": df["订单状态"],   # 已在过滤阶段归一化
        "省":       df["省"],
        "市":       df["市"],
    })
    # 过滤掉 SKU 为空的行
    products_df = products_df[products_df["SKU编码"] != ""].reset_index(drop=True)

    # ── orders_df（按订单号/出库单号去重，取收入）────────────────
    agg_dict = {
        "日期":     ("日期",     "first"),
        "下单时间": ("下单时间", "first"),
        "订单状态": ("订单状态", "first"),
        "商家收入": ("_ord_rev", "first"),
        "商品数量": ("_qty",     "sum"),
        "省":       ("省",       "first"),
        "市":       ("市",       "first"),
    }
    # 可选列：付款时间/发货时间不一定存在
    if "付款时间" in df.columns:
        agg_dict["支付时间"] = ("付款时间", "first")
    if "发货时间" in df.columns:
        agg_dict["发货时间"] = ("发货时间", "first")

    ord_agg = (
        df.groupby(order_id_col, sort=False)
        .agg(**agg_dict)
        .reset_index()
        .rename(columns={order_id_col: "主订单号"})
    )
    if "支付时间" in ord_agg.columns:
        ord_agg["支付时间"] = ord_agg["支付时间"].apply(_safe_str)
    if "发货时间" in ord_agg.columns:
        ord_agg["发货时间"] = ord_agg["发货时间"].apply(_safe_str)
    orders_df = ord_agg

    print(f"  [WDT] 格式={order_id_col} 数量列={qty_col} 收入列={unit_rev_col} "
          f"订单数={len(orders_df)} SKU行={len(products_df)}")
    return orders_df, products_df


# ─────────────────────────────────────────────────────────────────
# 统一入口：自动识别格式
# ─────────────────────────────────────────────────────────────────

def parse_store(
    store_df: pd.DataFrame,
    period_date: str = "2026-02-01",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    自动识别格式并调用对应解析器。
    返回标准 (orders_df, products_df)。
    """
    fmt = detect_format(store_df)
    if fmt == "orders":
        return orders_to_standard_format(store_df)
    else:
        return to_standard_format(store_df, period_date)


# ─────────────────────────────────────────────────────────────────
# 退货数据提取（从货品销售汇总表）
# ─────────────────────────────────────────────────────────────────

def extract_returns(df: pd.DataFrame, store_raw: str) -> pd.DataFrame:
    """
    从「货品销售汇总表」中提取指定店铺的退货数据。

    返回 DataFrame，列：
      SKU编码 | 货品名称 | 退货量 | 退货总金额

    退货量来源（优先级）：
      退货量 列 → 总销量 - 实际销售量
    退货总金额来源（优先级）：
      退货总金额 列 → 发货总金额 - 实际销售额
    """
    store_df = extract_store_df(df, store_raw)
    if store_df.empty:
        return pd.DataFrame(columns=["SKU编码", "货品名称", "退货量", "退货总金额"])

    def _n(col):
        return _num_col(store_df[col]) if col in store_df.columns else pd.Series([0.0] * len(store_df))

    # 退货量
    if "退货量" in store_df.columns:
        ret_qty = _n("退货量")
    else:
        ret_qty = (_n("总销量") - _n("实际销售量")).clip(lower=0)

    # 退货总金额
    if "退货总金额" in store_df.columns:
        ret_amt = _n("退货总金额")
    else:
        ret_amt = (_n("发货总金额") - _n("实际销售额")).clip(lower=0)

    sku  = store_df.get("货品编号",  pd.Series([""] * len(store_df))).apply(_safe_str).str.upper()
    name = store_df.get("货品名称",  pd.Series([""] * len(store_df))).apply(_safe_str)

    result = pd.DataFrame({
        "SKU编码":    sku,
        "货品名称":   name,
        "退货量":     ret_qty.values,
        "退货总金额": ret_amt.values,
    })

    # 只保留有实际退货的行
    result = result[
        (result["SKU编码"] != "") &
        ((result["退货量"] > 0) | (result["退货总金额"] > 0))
    ].reset_index(drop=True)
    return result
