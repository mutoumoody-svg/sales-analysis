"""
core/analyzer.py
分析引擎：成本匹配 + 生成所有分析表

输入：
  - orders_df   : 订单级 DataFrame（来自 platform loader）
  - products_df : 产品级 DataFrame（已拆 SKU）
  - cost_df     : 成本数据（可选，若无则毛利相关列为 NaN）

输出：包含所有分析结果的字典 {sheet名: DataFrame}
"""

import os
import re
import pandas as pd


# ── 成本数据加载 ──────────────────────────────────────────────────
COST_CODE_ALIASES  = ["货物编码", "货品编号", "货号", "SKU", "商品编号", "商家编码"]
COST_PRICE_ALIASES = ["单位成本", "成本价", "单价成本", "成本", "采购价", "产品成本"]


def load_cost(path: str) -> pd.DataFrame | None:
    """读取成本 Excel，返回 {SKU编码: 单位成本}。"""
    if not path:
        return None
    try:
        df = pd.read_excel(path, dtype=str)
        df.columns = df.columns.str.strip()
        code_col  = _find_col(df, COST_CODE_ALIASES)
        price_col = _find_col(df, COST_PRICE_ALIASES)
        if not code_col or not price_col:
            print(f"  [成本] 未找到编码/成本列，跳过成本匹配。列名：{list(df.columns)}")
            return None
        result = df[[code_col, price_col]].copy()
        result.columns = ["SKU编码", "单位成本"]
        result["SKU编码"]  = result["SKU编码"].str.strip()
        result["单位成本"] = pd.to_numeric(result["单位成本"], errors="coerce").fillna(0)
        result = result.drop_duplicates("SKU编码")
        print(f"  [成本] 加载 {len(result)} 个 SKU 成本")
        return result
    except Exception as e:
        print(f"  [成本] 加载失败：{e}")
        return None


def _find_col(df: pd.DataFrame, aliases: list) -> str | None:
    for alias in aliases:
        for col in df.columns:
            if alias in str(col):
                return col
    return None


# ── SKU 模糊匹配 ──────────────────────────────────────────────────
def _build_cost_lookup(cost_df: pd.DataFrame) -> dict:
    """构建 {SKU编码: 单位成本} 字典，所有 key 转大写去空格。"""
    return {str(k).strip().upper(): v
            for k, v in zip(cost_df["SKU编码"], cost_df["单位成本"])}


def _fuzzy_lookup(sku: str, lookup: dict) -> float:
    """
    杯身 + 杯带 分开匹配，成本相加。

    杯带后缀映射（销售编码后缀 → 成本表编码）：
      TB / TTB / BN  → STTEBTTB  茶棕色杯带
      GY / TGT / BTGT → STTEBTGT 灰色杯带
      LI / ELY / BTLISX → STTEBTLI 紫色杯带
      TSX / BSX       → STTEBTGT  灰色杯带（近似）
      YSG             → STTOKEYSG 延伸口套装
    """
    import re

    raw = str(sku).strip().upper()
    if not raw or raw in ("-", ""):
        return 0.0

    # 精确匹配（有些 SKU 本来就在成本表）
    if raw in lookup:
        return lookup[raw]

    # ── 杯带后缀识别 ────────────────────────────────────────────
    # 手动补录成本（无法通过规则匹配的特殊SKU，及各系列杯身基础成本）
    MANUAL_COST = {
        # ── 吸管杯系列（20oz）──
        "STTEWHI20DS20": 79.1,   # 20oz太妃糖吸管杯
        "STTEWHI20STMT": 79.1,   # 20oz燕麦奶吸管杯
        "STTEWHI20STBB": 79.1,   # 20oz冰薄荷吸管杯
        "STTEWHI20STSG": 79.1,   # 20oz时尚白吸管杯
        # ── 旧款缩写形式（ST前缀）──
        "STWHI12":       62.7,   # 时尚白12oz
        "STBLA12":       62.7,   # 奢华黑12oz
        # ── 配件/其他 ──
        "MKWJWP":        10.0,   # 配件杯盖售后运费款
        "S7SCUPHSGR":    33.0,   # 莫吉托薄荷品香杯
        "S7SCUPHSPK":    33.0,   # 覆盆子玫瑰品香杯（7oz）
        "STTOKERBH01":    5.0,   # STTOKE盈旋杯绒布袋
        # ── 杯带（25元/条）──
        "STTEBTTB":      25.0,   # 茶棕色杯带
        "STTEBTGT":      25.0,   # 灰色杯带
        "STTEBTLI":      25.0,   # 紫色杯带
        # ── 配件 ──
        "STTOKEYSG":     30.0,   # 延伸盖套装（基础款）
        "STTOKEHEBB":    30.0,   # 延伸盖-冰薄荷
        "STTOKEHEMT":    30.0,   # 延伸盖-燕麦奶
        "STTOKEHEBP":    30.0,   # 延伸盖-粉玫酿
        "NEWSTTOKEBG2":       10.0,  # 新款旋转盖
        "NEWSTTOKEBG2-DY":    10.0,  # 新款旋转盖-软曲奇
        "NEWSTTOKEBG2-BB":    10.0,  # 新款旋转盖-冰薄荷
        "NEWSTTOKEBG2-SR":    10.0,  # 新款旋转盖-绯红
        "STTOKETEAINF":  25.0,   # 茶水冲泡器
        "STTOKECBSL20":  15.0,   # 20oz杯盖
        # ── 硅胶勺 ──
        "STTOKEGJS":      3.5,   # 硅胶勺
        "STHARIO":       200.0,  # Hario Skerton Plus 手磨机
        "HARIO":         220.0,  # Hario STTOKE联名礼盒套装
        "MCTZ-NATURAL*1":  2.0,  # 云傣寨挂耳咖啡1片
        # ── 分享壶 ──
        "STTOKESJHCB":  200.0,   # 不锈钢分享壶 20oz 晨雾白
        "STTOKESJHEG":  200.0,   # 不锈钢分享壶 20oz 暮色灰
        # ── MOODY BOTTLE 水瓶 ──
        "MCBOTBLWHI":    50.0,   # 好有水瓶 皓月白
        "MCBOTBLAM":     50.0,   # 好有水瓶mini 暗夜黑
        # ── 7oz 盈旋杯 ──
        "STTOKERR7":     40.0,   # 覆盆子玫瑰7oz
        "STTOKEMM7":     40.0,   # 莫吉托薄荷7oz
        "STTOKECG7":     40.0,   # 莫尼耶香槟7oz
        "S7SCUPHSBM":    40.0,   # 盈旋杯【单只】玛格丽特蓝7oz
        "S7SCUPHSBL":    40.0,   # 盈旋杯【单只】朗姆经典黑7oz
        # ── 20oz 吸管套装（STTOKEST* = 50）──
        "STTOKESTBB":    50.0,   # 吸管套-冰薄荷
        "STTOKESTMT":    50.0,   # 吸管套-燕麦奶
        "STTOKESTSG":    50.0,   # 吸管套-火山灰
        "STTOKESTLB":    50.0,   # 吸管套-奢华黑
        "STTOKESTDS":    50.0,   # 吸管套-太妃糖
        # ── 20oz 单支吸管（STTOKES* = 20）──
        "STTOKESSG":     20.0,   # 单吸管-火山灰
        "STTOKESLB":     20.0,   # 单吸管-奢华黑
        "STTOKESBB":     20.0,   # 单吸管-冰薄荷
        "STTOKESMT":     20.0,   # 单吸管-燕麦奶
        "STTOKESDS":      7.0,   # STTOKE 20oz吸管太妃糖
        # ── 赠品 ──
        "BNMS":           2.5,   # 木勺赠品
        "LSBS":           2.0,   # 杯刷赠品
        "MCTZ-NATURAL*1BS": 6.0, # 杯刷+挂耳赠品
        "MCTZ-NATURAL*2":   5.0, # 挂耳咖啡赠品
        # ── 2026新色杯身（粉玫酿/绿橄榄，不含杯带）──
        "STTOKELESBP12":  71.7,  # 粉玫酿12oz
        "STTOKELESBP16":  74.8,  # 粉玫酿16oz
        "STTOKELESIG12":  71.7,  # 绿橄榄12oz
        "STTOKELESIG16":  74.8,  # 绿橄榄16oz
        # ── MOOMIN联名系列（80元杯身）──
        "STTOKEMOOMINW16":  80.0,  # 桥畔初遇16oz
        "STTOKEMOOMINS20":  80.0,  # 星光私语20oz
        "STTOKEMOOMINKSA":  25.0,  # MOOMIN便携杯带
        "STTOKEMOOMINKS":   15.0,  # MOOMIN钥匙扣-史力奇
        "STTOKEMOOMINKM":   16.48, # MOOMIN钥匙扣-姆明
        "STTOKEMOOMINKLM":  16.48, # MOOMIN钥匙扣-亚美
        # ── 夜光海洋系列（80元）──
        "STTEWHALE16":    80.0,   # 鲸鱼16oz
        "STTEWHALE12":    80.0,   # 鲸鱼12oz
        "STTOKEOSMRS16":  80.0,   # 蝠鲼16oz旋盖
        "STTOKEOSMRS12":  80.0,   # 蝠鲼12oz旋盖
        "STTOKEOSD16":    80.0,   # 海豚16oz旋盖
        "STTOKEOSD12":    80.0,   # 海豚12oz旋盖
        "STTESEATUR12":   80.0,   # 海龟12oz
        # ── 巴恩蜂蜜系列 ──
        "BNMGO30":         20.0,  # MGO30+ 单瓶250g
        "BNMGO30*2":       40.0,  # MGO30+ 250g*2
        "BNMGO100":        40.0,  # MGO100+ 单瓶250g
        "BNMGO100-500":    75.0,  # MGO100+ 单瓶500g
        "BNMGO300-250":    60.0,  # MGO300+ 单瓶250g
        "BNMGO550-250":    85.0,  # MGO550+ 单瓶250g
        "BNMGO100*2GFBOX": 100.0, # MGO100+ 2瓶礼盒
        "BN100LH":         90.0,  # MGO100+ 花花礼盒（2瓶）
        "BN100MN":         90.0,  # MGO100+ 马年礼盒（2瓶）
        "BN300LH":        150.0,  # MGO300+ 马年礼盒（2瓶）
        "BNPRHY":          18.0,  # 纯蜂蜜250g 单瓶
        "BNPRHY2":         36.0,  # 纯蜂蜜250g*2
        "BNMGO100HHLH":    90.0,  # MGO100+ 2罐礼盒(恒好)
        # ── 巴恩醋系列 ──
        "BARNESCV":        18.0,  # 苹果醋500ml 单瓶
        "BARNESHONYYV":    28.0,  # 蜂蜜苹果醋500ml 单瓶
        "BARNESCVBARNESHONYYV": 50.0, # 苹果醋+蜂蜜苹果醋组合
        # ── 康蜜乐系列 ──
        "CPH375JN":        50.0,  # 经典蜂蜜375g挤拧装
        "CPHCANDY":        15.0,  # 麦卢卡蜂蜜硬糖
        "CPH340":          45.0,  # 经典蜂蜜340g倒立装
        "CKPH340":         32.5,  # 康蜜乐CAPILANO儿童蜂蜜 倒立装340g
        # ── 徽章系列 ──
        "STTOKEPPB":  10.0,   # STTOKE徽章黑色
        "STTOKEPPL":  10.0,   # STTOKE徽章淡紫色
        "STTOKEPPW":  10.0,   # STTOKE徽章白色
        "STTOKEPPY":  10.0,   # STTOKE徽章黄色
        # ── 包装 / 配件 / 耗材 ──
        "KJJZX-6":      1.5,   # STTOKE可降解纸箱-6号
        "KJJZX-7":      1.35,  # STTOKE可降解纸箱-7号
        "STTOKEXCC":    1.3,   # STTOKE宣传册2024
        "STTOKECD":     0.17,  # STTOKE介绍卡片
        "TTOKECD":      0.17,  # STTOKE介绍卡片（别名）
        "STTOKEBG2":   10.0,   # STTOKE杯盖旋转盖
        "TTOKEBG2":    10.0,   # STTOKE杯盖旋转盖（别名）
        "NEWSTTOKEBG2": 10.0,  # [新款]STTOKE杯盖旋转盖
        "LSBS":          2.5,   # 杯刷
        "STTOKEFBD":     5.5,   # STTOKE帆布袋
        "STTEBTTBSX":   15.0,   # STTOKE便携杯带(茶棕)双扣款（独立商品）
        "STTOKEBLSX":   45.0,   # STTOKE便携杯带(黑色限定)双扣款
        "STDZGFBAG":     3.6,   # STTOKE定制礼袋
        "MKTZ":          0.5,   # 慕咖3D立体贴纸
        # ── 巴恩包装耗材 ──
        "BNKDH-8":      0.95,  # 巴恩快递盒-8号
        "BANNESCS":     1.0,   # 巴恩2025新册子
        "BNHHBOX":      9.0,   # 巴恩天然2025-花花礼盒
        "BNHHBAG":      1.5,   # 巴恩天然2025-花花礼袋
        # ── 新增SKU（2026-05更新）──
        "CMGO100HN250":  40.0,  # 康蜜乐CAPILANO MGO100+蜂蜜 倒立装250g
        "CLOW250":       32.09, # 康蜜乐低升糖蜂蜜250g倒立装
        "BNMGO850-500":  350.0, # 巴恩天然活性麦努卡蜂蜜 MGO850+ 500g
        "BNMGO1050-500": 350.0, # 巴恩天然活性麦努卡蜂蜜 MGO1050+ 500g
        "BNMGO300-500":  157.31,# 巴恩天然活性麦努卡蜂蜜 MGO300+ 500g
        "CPH1KG":        79.5,  # 康蜜乐蜂蜜（家庭装）1KG
        "CPH500":        35.12, # 康蜜乐蜂蜜倒立装500g
        "CPH250":        20.13, # 康蜜乐经典蜂蜜250g倒立装
        "CMGO30HN340":   37.95, # 康蜜乐CAPILANO麦卢卡MGO30+蜂蜜 倒立装340g
        "CKPH340-1":      0.0,  # 康蜜乐CAPILANO儿童蜂蜜 340g赠品（虚拟）
        "S7SCUPHSYL":    40.0,  # 盈旋杯【单只】含羞草柔黄7oz
        "MCZG-NATURAL*1":  2.0, # 云之光挂耳咖啡1片
        "MC-HONEYPROCESS*1": 2.0, # 云雨林挂耳咖啡1片
        "MC-FOREST*1":    2.0,  # 云森林挂耳咖啡1片
        "BNBAGNEW":      13.5,  # 抽拉款-巴恩天然蜂蜜礼袋
        "BNGFBOXSNEW":    2.0,  # 抽拉款-巴恩天然蜂蜜礼盒250g*2
        "STTOKEMB7":     75.71, # STTOKE盈旋杯 【玛格丽特蓝7oz】
        "STTOKEMY7":     75.71, # STTOKE盈旋杯 【含羞草柔黄7oz】
        "BNMNBAG":        1.5,  # 巴恩天然2025-马年礼袋
        "BNMNBOX":        9.0,  # 巴恩天然2025-马年礼盒
        "MCBWSPTEAM":    28.0,  # 慕咖Moody×海底小纵队儿童保温水瓶-Team
        "MCBOTHDWSH":    50.0,  # 慕咖moody海底小纵队皓月白-Say Hi
        "MCBOTHDBGJ":    50.0,  # 慕咖moody海底小纵队暗夜黑-呱唧
        "MKSYBWO1":      45.0,  # 慕咖Moody随饮杯【奶油白】
        "MKSYBO04":      45.0,  # 慕咖Moody随饮杯【珊瑚橙】
        "MVCBULLG":      40.0,  # 慕咖Mood Cup元气晴空保温杯（L）带logo
        "MCITYG":        40.0,  # 慕咖城市咖啡杯（抹茶绿）
        "MCTZ10BOX":     20.0,  # MoodyCoffee云傣寨挂耳*10盒装
        "MSYBDZ001":     11.5,  # 慕咖Moody随饮杯杯带棕色
        "MKSYBS-BLACK":  10.0,  # 慕咖Moody随饮杯杯盖-黑色
        "MKSYBS-WHITE":  10.0,  # 慕咖Moody随饮杯杯盖-白色
        "BAEN1050YF":     2.3,  # 巴恩天然1050腰封（500g单瓶）
        "BAEN850YF":      2.3,  # 巴恩天然850腰封（500g单瓶）
        "BAENBOX":       12.0,  # 巴恩天然850&1050礼盒外盒（500g单瓶）
        "STDZGFBOX":     18.5,  # STTOKE定制礼盒
        "STNCGP2":        3.0,  # STTOKE礼盒内衬组合2（16oz+挂耳咖啡）
        "STNCGP5":        3.0,  # STTOKE礼盒内衬组合5（12oz+16oz）
        "MOODYBLBSJ":    30.0,  # 颜色随机玻璃杯
        "BNWJXN":         0.0,  # 巴恩文件物品（虚拟）
        "MFFBT":          2.0,  # Baby Towel
        # ── 2026-07-02 补录（来自库存盘点）──
        "STTOKEBG3":      20.0,   # STTOKE杯盖透明旋转盖
        "STTOKESTIG":     10.0,   # STTOKE 20oz吸管套绿橄榄
        "STTOKESTBP":     10.0,   # STTOKE 20oz吸管套粉玫酿
        "STTOKEZJW":      10.0,   # STTOKE单个方形展架白色
        "STSZ":           10.0,   # STTOKE量勺夹
        "STTOKELB7":      40.0,   # STTOKE盈旋杯朗姆经典黑7OZ
        "GQCQSTTOKESPCU": 60.0,   # 广汽传祺×STTOKE定制款
        "STTOKESX76":     40.0,   # STTOKE盈旋杯夏多内银灰7OZ
        "STTOKEZJB":      20.0,   # STTOKE单个方形展架黑色
        "STTESWIRL CUP":  50.0,   # STTOKE家用杯（SET）
        "NEWBNMGO100":    39.29,  # 巴恩天然麦卢卡蜂蜜MGO100+ 250g
        "NEWBNMGO1050-250": 55.91, # 巴恩天然麦卢卡蜂蜜MGO1050+ 250g
        "NEWNBNMGO300-250": 81.65, # 巴恩天然麦卢卡蜂蜜MGO300+ 250g
        "NEWBNMGO850-250":  141.71, # 巴恩天然麦卢卡蜂蜜MGO850+ 250g
        "NEWBNMGO550-250":  163.16, # 巴恩天然麦卢卡蜂蜜MGO550+ 250g
        "CKPH340-1":      20.0,   # 康蜜乐CAPILANO儿童蜂蜜赠品
        "BOTBLWHI":       30.0,   # 好有水瓶皓月白
        "MCBWSPBF":       30.0,   # 慕咖×海底小纵队儿童保温水瓶缤纷
        "MMC-JJ":         30.0,   # 月亮杯
        "MKSYBB02":       30.0,   # 慕咖Moody随饮杯星钻黑
        "MVCGNSLG":       30.0,   # 慕咖Mood Cup元气森屿S带logo
        "MCBOTHDRUN":     30.0,   # 慕咖moody海底小纵队暗夜黑奔跑
        "MKSYBGO3":       30.0,   # 慕咖Moody随饮杯青柠绿
        "BOTBLA":         30.0,   # 好有水瓶暗夜黑
        "MKSYBSO6":       30.0,   # 慕咖Moody随饮杯海风蓝
        "MVCGNLLG":       30.0,   # 慕咖Mood Cup元气森屿L带logo
        "MVCPKL":         30.0,   # 慕咖Mood Cup半糖女孩L
        "BOTBLMINIA":     30.0,   # 好有水瓶mini暗夜黑
        "MCGRE12":        30.0,   # 慕咖MoodCone蛋筒便携杯苏打绿
        "MVCYESLG":       30.0,   # 慕咖Mood Cup柠檬汽水S带logo
        "MCITYWLG":       30.0,   # 慕咖城市咖啡杯杏仁白带logo
        "MCBLU12":        30.0,   # 慕咖MoodCone蛋筒便携杯冰雪蓝
        "MVCGYSLG":       30.0,   # 慕咖Mood Cup元气骑士S带logo
        "MVCPKSLG":       30.0,   # 慕咖Mood Cup半糖女孩S带logo
        "MKWQG":          30.0,   # 慕咖x味全保温咖啡杯绿
        "MVCGYS":         30.0,   # 慕咖Mood Cup元气骑士S
        "BOTBLMINIWHI":   30.0,   # 好有水瓶mini皓月白
        "MKSYBPO5":       30.0,   # 慕咖Moody随饮杯风信紫
        "MVCPKLLG":       30.0,   # 慕咖Mood Cup半糖女孩L带logo
        "MVCYELLG":       30.0,   # 慕咖Mood Cup柠檬汽水L带logo
        "MBCMH12":        30.0,   # 慕咖Mood Cup梦幻随行杯
        "MBWY12":         30.0,   # 慕咖Mood Cup微雨随行杯
        "STALPAKA":      200.0,   # Alpaka Sidekick Bag随行包
        "STDPRESS":      100.0,   # Delter Coffee Press D特压
    }
    if raw in MANUAL_COST:
        return MANUAL_COST[raw]

    STRAP_MAP = {
        "TTB":      "STTEBTTB",   # 茶棕色杯带
        "TB":       "STTEBTTB",
        "BN":       "STTEBTTB",
        "TGT":      "STTEBTGT",   # 灰色杯带
        "GY":       "STTEBTGT",
        "BTGT":     "STTEBTGT",
        "TSX":      "STTEBTGT",   # 灰色（近似）
        "BTLISX":   "STTEBTLI",   # 紫色杯带
        "ELY":      "STTEBTLI",
        "LI":       "STTEBTLI",
        "BSX":      "STTEBTTB",   # 茶棕（近似）
        "BTTBSX":   "STTEBTTB",
        "YSG":      "STTOKEYSG",  # 延伸口套装 40元
        # ── 2026新色专用全称杯带（+号后整段）──
        "STTEBTLISX":  "STTEBTLI",   # 紫色杯带（完整编码）
        "STTEBTTBSX":  "STTEBTTB",   # 茶棕杯带（完整编码）
        "STTEBTGTSX":  "STTEBTGT",   # 灰色杯带（完整编码）
    }

    strap_cost = 0.0
    strap_code = None

    def _strap_price(code: str) -> float:
        """杯带/配件：先查成本文件，再查 MANUAL_COST。"""
        return lookup.get(code, MANUAL_COST.get(code, 0.0))

    # 先处理 '+' 拼接的杯带（如 STTOKEMSG16+TTB）
    if "+" in raw:
        parts = raw.split("+", 1)
        cup_raw   = parts[0]
        strap_sfx = parts[1]
        if strap_sfx in STRAP_MAP:
            sc = STRAP_MAP[strap_sfx]
            strap_cost = _strap_price(sc)
            strap_code = sc
        elif strap_sfx in lookup or strap_sfx in MANUAL_COST:
            strap_cost = _strap_price(strap_sfx)
            strap_code = strap_sfx
        raw = cup_raw   # 剩下的是杯身
    else:
        # 直接拼接的杯带后缀（如 STTOKEDS12TB）
        for sfx in sorted(STRAP_MAP.keys(), key=len, reverse=True):   # 长后缀优先
            if raw.endswith(sfx):
                sc = STRAP_MAP[sfx]
                strap_cost = _strap_price(sc)
                strap_code = sc
                raw = raw[: -len(sfx)]   # 剩下杯身编码
                break

    # ── 杯身匹配 ────────────────────────────────────────────────
    cup_candidates = [raw]
    for n in (2, 3, 4, 5):
        stripped = re.sub(r"[A-Z]{" + str(n) + r"}$", "", raw)
        if stripped != raw:
            cup_candidates.append(stripped)

    # 前缀互换：STTOKE ↔ STTE ↔ STT（短前缀，如STTBLA→STTOKEBLA）
    swaps = []
    for c in cup_candidates:
        if c.startswith("STTOKE"):
            swaps.append("STTE" + c[6:])
            swaps.append("STT"  + c[6:])   # STTOKE→STT 短形式
        elif c.startswith("STTE"):
            swaps.append("STTOKE" + c[4:])
            swaps.append("STT"    + c[4:])
        elif c.startswith("STT") and not c.startswith("STTOKE") and not c.startswith("STTE"):
            swaps.append("STTOKE" + c[3:]) # STT→STTOKE 补全
            swaps.append("STTE"   + c[3:])
    cup_candidates += swaps

    cup_cost = 0.0
    for c in cup_candidates:
        if c in lookup:
            cup_cost = lookup[c]
            break
        if c in MANUAL_COST:
            cup_cost = MANUAL_COST[c]
            break

    # ── 尺寸兜底：STTOKE/STTE 系列标准杯（特殊系列已在 MANUAL_COST 中）──
    # 适用于 STTOKEHG16 / STTOKEMT12 / STTOKELCSBP08 等数字结尾的编码
    if cup_cost == 0.0:
        sz_m = re.search(r'(\d+)$', raw)
        if sz_m and re.match(r'(STTOKE|STTE|STT)', raw):
            sz = int(sz_m.group(1).lstrip('0') or '0')
            cup_cost = {8: 70.0, 12: 62.7, 16: 74.8, 20: 79.1}.get(sz, 0.0)

    return round(cup_cost + strap_cost, 4)


# ── 成本注入 ──────────────────────────────────────────────────────
def inject_cost(products_df: pd.DataFrame, cost_df: pd.DataFrame | None) -> pd.DataFrame:
    """将单位成本合并进产品明细，计算总成本/毛利润/毛利率。"""
    df = products_df.copy()

    # 始终构建 lookup（cost_df 有数据则合并，否则为空 dict，MANUAL_COST 仍可命中）
    lookup = _build_cost_lookup(cost_df) if cost_df is not None else {}
    df["单位成本"] = df["SKU编码"].apply(lambda s: _fuzzy_lookup(s, lookup))

    real_mask = df.get("是否赠品", pd.Series(["正品"]*len(df))) == "正品"
    matched = (df.loc[real_mask, "单位成本"] > 0).sum()
    total   = real_mask.sum()
    no_cost = df.loc[real_mask & (df["单位成本"] == 0), "SKU编码"].unique()
    src_label = "成本文件+内置" if cost_df is not None else "内置MANUAL_COST"
    print(f"  [成本匹配] 正品行 {total}，命中 {matched}（{matched/total*100:.1f}%）[{src_label}]")
    if len(no_cost) > 0:
        print(f"  [待录入]  {len(no_cost)} 个SKU暂无成本：{list(no_cost[:8])}")
    df.loc[real_mask & (df["单位成本"] == 0), "成本状态"] = "待录入"
    df.loc[real_mask & (df["单位成本"] > 0), "成本状态"] = "已匹配"
    df.loc[~real_mask, "成本状态"] = "赠品"

    df["单位成本"] = pd.to_numeric(df["单位成本"], errors="coerce").fillna(0)
    df["销量"]     = pd.to_numeric(df.get("销量"),     errors="coerce").fillna(0)
    df["商家收入"] = pd.to_numeric(df.get("商家收入"), errors="coerce").fillna(0)

    df["总成本"]   = df["单位成本"] * df["销量"]
    df["毛利润"]   = df["商家收入"] - df["总成本"]
    df["毛利率"]   = df.apply(
        lambda r: r["毛利润"] / r["商家收入"] if r["商家收入"] != 0 else 0, axis=1
    )
    return df


# ── 各分析表生成 ──────────────────────────────────────────────────
def load_ads(path: str) -> pd.DataFrame | None:
    """读取天猫营销场景报表。path 支持多个文件路径用分号分隔，自动合并。"""
    if not path:
        return None

    def _load_one(p: str) -> pd.DataFrame | None:
        p = p.strip()
        if not p:
            return None
        try:
            ext = os.path.splitext(p)[1].lower()
            if ext in (".xlsx", ".xls"):
                df = pd.read_excel(p, dtype=str)
            else:
                df = None
                for enc in ["utf-8-sig", "gbk", "gb18030"]:
                    try:
                        df = pd.read_csv(p, encoding=enc, dtype=str)
                        break
                    except UnicodeDecodeError:
                        continue
                if df is None:
                    raise ValueError(f"无法用任何编码读取文件 {p}")
            df.columns = df.columns.str.strip()
            for col in ["花费", "总成交金额", "总成交笔数"]:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
            return df
        except Exception as e:
            print(f"  [广告] 加载失败 {p}：{e}")
            return None

    paths = [p for p in path.split(";") if p.strip()]
    frames = [_load_one(p) for p in paths]
    frames = [f for f in frames if f is not None]
    if not frames:
        return None

    result = pd.concat(frames, ignore_index=True) if len(frames) > 1 else frames[0]
    total = result["花费"].sum() if "花费" in result.columns else 0
    print(f"  [广告] 加载推广报表：{len(result)} 行（{len(frames)} 个文件），总花费 {total:,.2f} 元")
    return result


def build_all(orders_df: pd.DataFrame,
              products_df: pd.DataFrame,
              cost_df: pd.DataFrame | None,
              ads_df: pd.DataFrame | None = None,
              platform: str = "",
              store: str = "") -> dict[str, pd.DataFrame]:
    """返回所有分析表的字典，key = Sheet 名称。
    platform: '天猫' / '抖音' / '京东' / '小红书'
    store:    店铺名称，用于判断品牌税率（慕咖13%/巴恩天然9%）"""

    # 注入成本
    prod = inject_cost(products_df, cost_df)

    # 售后订单与正常订单分离（用 .values 避免索引不对齐报错）
    aftersale_flag_o = (orders_df["售后类型"].values == "售后退款") \
        if "售后类型" in orders_df.columns \
        else ([False] * len(orders_df))
    aftersale_flag_p = (prod["售后类型"].values == "售后退款") \
        if "售后类型" in prod.columns \
        else ([False] * len(prod))

    import numpy as np
    aftersale_flag_o = np.array(aftersale_flag_o, dtype=bool)
    aftersale_flag_p = np.array(aftersale_flag_p, dtype=bool)

    normal_orders = orders_df[~aftersale_flag_o].copy()
    normal_prod   = prod[~aftersale_flag_p].copy()
    after_orders  = orders_df[aftersale_flag_o].copy()
    after_prod    = prod[aftersale_flag_p].copy()

    sheets = {}

    # ── Sheet 1：订单明细 ─────────────────────────────────────────
    sheets["订单明细"] = _sheet_order_detail(normal_orders)

    # ── Sheet 2：产品明细 ─────────────────────────────────────────
    sheets["产品明细"] = _sheet_product_detail(normal_prod)

    # ── Sheet 3：SKU 汇总 ─────────────────────────────────────────
    sheets["SKU汇总"] = _sheet_sku_summary(normal_prod)

    # ── Sheet 4：日期趋势 ─────────────────────────────────────────
    sheets["日期趋势"] = _sheet_daily_trend(normal_orders, normal_prod)

    # ── Sheet 5：流量来源分析 ─────────────────────────────────────
    sheets["流量来源"] = _sheet_traffic(normal_orders, normal_prod)

    # ── Sheet 6：发货情况 ─────────────────────────────────────────
    sheets["发货情况"] = _sheet_shipping(normal_orders)

    # ── Sheet 7：毛利汇总（仪表板）────────────────────────────────
    sheets["毛利汇总"] = _sheet_profit_summary(normal_orders, normal_prod, ads_df,
                                               platform=platform, store=store)

    # ── Sheet 8：售后相关销售 ─────────────────────────────────────
    if not after_orders.empty:
        sheets["售后相关销售"] = _sheet_aftersale(after_orders, after_prod)

    return sheets


# ─────────────────────── Sheet 函数 ──────────────────────────────

def _sheet_order_detail(orders: pd.DataFrame) -> pd.DataFrame:
    """订单明细：保留所有字段，格式化输出列。"""
    want = [
        "主订单号", "子订单号", "日期", "下单时间", "支付时间",
        "发货时间", "完成时间", "支付方式", "订单状态", "售后状态",
        "商品数量", "标价总额", "应付金额", "商家收入", "优惠总额",
        "平台优惠", "商家优惠", "达人优惠", "商家改价",
        "流量类型", "达人昵称", "省", "市", "区", "仓库",
    ]
    cols = [c for c in want if c in orders.columns]
    df = orders[cols].copy()
    df = df.sort_values("日期", ascending=True) if "日期" in df.columns else df
    return df


def _sheet_product_detail(prod: pd.DataFrame) -> pd.DataFrame:
    """产品明细（已拆 SKU，含赠品标记 & 成本列）。"""
    want = [
        "主订单号", "日期", "下单时间",
        "SKU编码", "商品名称", "是否赠品",
        "销量", "标价", "商家收入", "单位成本", "总成本", "毛利润", "毛利率",
        "订单状态", "流量类型", "达人昵称",
    ]
    cols = [c for c in want if c in prod.columns]
    df = prod[cols].copy()
    df = df.sort_values(["日期", "SKU编码"], ascending=[True, True]) \
        if "日期" in df.columns else df
    return df


def _sheet_sku_summary(prod: pd.DataFrame) -> pd.DataFrame:
    """
    SKU 汇总：全部物料（正品 + 赠品/配件/包装）按货号聚合。
    同货号不同标题视为同一产品。
    正品：显示销量/销售额/成本/毛利；赠品/配件：显示赠出次数/成本。
    """

    def _best_name(series):
        m = series.mode()
        return m.iloc[0] if not m.empty else series.iloc[0]

    COLS = ["SKU编码", "商品名称", "类型", "销量/赠出次数", "订单数",
            "总销售额", "总成本", "总毛利润", "毛利率", "客单价", "单位成本"]

    # ── 正品 ──────────────────────────────────────────────────────
    real = prod[prod["是否赠品"] == "正品"].copy()
    real_grp = real.groupby("SKU编码", dropna=False).agg(
        **{"销量/赠出次数": ("销量",     "sum"),
           "总销售额":      ("商家收入", "sum"),
           "总成本":        ("总成本",   "sum"),
           "总毛利润":      ("毛利润",   "sum"),
           "订单数":        ("主订单号", "nunique")},
    ).reset_index()
    real_grp["商品名称"] = real_grp["SKU编码"].map(
        real.groupby("SKU编码")["商品名称"].agg(_best_name)
    )
    real_grp["类型"] = "正品"
    real_grp["毛利率"] = real_grp.apply(
        lambda r: r["总毛利润"] / r["总销售额"] if r["总销售额"] != 0 else 0, axis=1
    )
    real_grp["客单价"] = real_grp.apply(
        lambda r: r["总销售额"] / r["订单数"] if r["订单数"] != 0 else 0, axis=1
    )
    # 单位成本：取该 SKU 正品行中首个有效（>0）的单位成本
    if "单位成本" in real.columns:
        sku_cost_map = real.groupby("SKU编码")["单位成本"].agg(
            lambda s: float(s[s > 0].iloc[0]) if (s > 0).any() else 0.0
        )
        real_grp["单位成本"] = real_grp["SKU编码"].map(sku_cost_map).fillna(0.0)
    else:
        real_grp["单位成本"] = 0.0
    real_out = real_grp[COLS].sort_values("总销售额", ascending=False)

    # ── 赠品 / 配件 ───────────────────────────────────────────────
    gift = prod[prod["是否赠品"] != "正品"].copy()
    parts = [real_out]

    if not gift.empty:
        # 每一行算赠出1次（原始数据赠品 销量=0 仅作占位）
        gift["_cnt"] = 1
        # SKU编码为空时用商品名称做分组键（避免所有赠品合并为一行）
        gift["_grp_key"] = gift["SKU编码"].where(
            gift["SKU编码"].notna() & (gift["SKU编码"] != ""),
            other=gift["商品名称"]
        )
        gift_grp = gift.groupby("_grp_key", dropna=False).agg(
            **{"SKU编码":       ("SKU编码",    _best_name),
               "商品名称":      ("商品名称",   _best_name),
               "销量/赠出次数": ("_cnt",       "sum"),
               "总销售额":      ("商家收入",   "sum"),   # 通常=0
               "_单位成本":     ("单位成本",   "mean"),  # 同SKU/名称单价取均值
               "订单数":        ("主订单号",   "nunique")},
        ).reset_index(drop=True)
        # 赠品总成本 = 单位成本 × 赠出次数（销量=0不能用，用行计数）
        gift_grp["总成本"]   = gift_grp["_单位成本"] * gift_grp["销量/赠出次数"]
        gift_grp["总毛利润"] = -gift_grp["总成本"]   # 赠品无收入，成本即损耗
        gift_grp["总销售额"] = 0.0
        gift_grp["类型"]   = "赠品/配件"
        gift_grp["毛利率"] = 0.0
        gift_grp["客单价"] = 0.0
        gift_grp["单位成本"] = gift_grp["_单位成本"]
        gift_out = gift_grp[COLS].sort_values("销量/赠出次数", ascending=False)

        # 插入分隔行
        sep = pd.DataFrame([{c: ("── 赠品 / 配件 / 包装 ──" if c == "商品名称" else "")
                              for c in COLS}])
        parts += [sep, gift_out]

    result = pd.concat(parts, ignore_index=True)
    return result


def _sheet_daily_trend(orders: pd.DataFrame, prod: pd.DataFrame) -> pd.DataFrame:
    """日期趋势：每日订单数、销量、收入、毛利。"""
    # 订单维度
    o = orders.copy()
    o["日期"] = pd.to_datetime(o["日期"], errors="coerce")
    ord_grp = o.groupby("日期").agg(
        订单数   = ("主订单号", "nunique"),
        总收入   = ("商家收入", "sum"),
    ).reset_index()

    # 产品维度（正品）
    real = prod[prod["是否赠品"] == "正品"].copy()
    real["日期"] = pd.to_datetime(real["日期"], errors="coerce")
    prod_grp = real.groupby("日期").agg(
        总销量   = ("销量",     "sum"),
        总成本   = ("总成本",   "sum"),
        总毛利润 = ("毛利润",   "sum"),
    ).reset_index()

    merged = pd.merge(ord_grp, prod_grp, on="日期", how="outer").fillna(0)
    merged["毛利率"] = merged.apply(
        lambda r: r["总毛利润"] / r["总收入"] if r["总收入"] != 0 else 0, axis=1
    )
    merged = merged.sort_values("日期").reset_index(drop=True)
    return merged


def _sheet_traffic(orders: pd.DataFrame, prod: pd.DataFrame) -> pd.DataFrame:
    """流量来源分析：按 流量类型 × 达人昵称 聚合。"""
    real = prod[prod["是否赠品"] == "正品"].copy()
    # 旺店通等无流量字段的平台，补默认值
    if "流量类型" not in real.columns:
        real["流量类型"] = "未知"
    if "达人昵称" not in real.columns:
        real["达人昵称"] = "自然流量"
    grp = real.groupby(["流量类型", "达人昵称"], dropna=False).agg(
        订单数   = ("主订单号", "nunique"),
        总销量   = ("销量",     "sum"),
        总销售额 = ("商家收入", "sum"),
        总毛利润 = ("毛利润",   "sum"),
    ).reset_index()

    total_sale = grp["总销售额"].sum()
    grp["销售额占比"] = grp["总销售额"].apply(
        lambda x: x / total_sale if total_sale != 0 else 0
    )
    grp["毛利率"] = grp.apply(
        lambda r: r["总毛利润"] / r["总销售额"] if r["总销售额"] != 0 else 0, axis=1
    )
    return grp.sort_values("总销售额", ascending=False).reset_index(drop=True)


def _sheet_shipping(orders: pd.DataFrame) -> pd.DataFrame:
    """发货情况：订单状态分布 + 未发货明细。"""
    o = orders.copy()

    # 状态汇总
    status_grp = o.groupby("订单状态").agg(
        订单数 = ("主订单号", "nunique"),
        总收入 = ("商家收入", "sum"),
    ).reset_index()
    total = status_grp["订单数"].sum()
    status_grp["占比"] = status_grp["订单数"] / total if total else 0

    # 已发货 / 未发货明细
    ship_col = "发货时间"
    if ship_col in o.columns:
        unshipped_cols = [c for c in [
            "主订单号", "日期", "下单时间", "订单状态",
            "商家收入", "达人昵称", "省", "市",
        ] if c in o.columns]
        unshipped = o[
            (o["订单状态"] == "已发货") &
            (o[ship_col].isna() | (o[ship_col] == ""))
        ][unshipped_cols].copy()
    else:
        unshipped = pd.DataFrame()

    # 合并：状态汇总在上，未发货明细在下（空行分隔）
    spacer = pd.DataFrame([{"订单状态": "── 待发货明细 ──"}])
    result = pd.concat(
        [status_grp, spacer, unshipped] if not unshipped.empty else [status_grp],
        ignore_index=True
    )
    return result


def _sheet_profit_summary(orders: pd.DataFrame, prod: pd.DataFrame,
                          ads_df: pd.DataFrame | None = None,
                          platform: str = "",
                          store: str = "") -> pd.DataFrame:
    """毛利汇总仪表板：全局指标 + 广告ROI + Top 10 SKU。"""
    real = prod[prod["是否赠品"] == "正品"].copy()
    gift = prod[prod["是否赠品"] != "正品"].copy()

    total_orders    = orders["主订单号"].nunique()
    total_revenue   = orders["商家收入"].sum() if "商家收入" in orders.columns else 0
    total_qty       = real["销量"].sum()
    product_cost    = real["总成本"].sum()                    # 正品成本
    # 赠品/包装：每行 = 赠出1件，成本 = 单位成本（总成本因销量=0无效，直接用单价加总）
    gift_cost       = gift["单位成本"].sum() if "单位成本" in gift.columns else 0
    total_cost      = product_cost + gift_cost               # 综合总成本
    total_profit    = total_revenue - total_cost             # 真实毛利润
    avg_margin      = total_profit / total_revenue if total_revenue != 0 else 0
    avg_order_val   = total_revenue / total_orders if total_orders != 0 else 0

    summary_rows = [
        {"指标": "统计周期",          "数值": f"{orders['日期'].min()} ~ {orders['日期'].max()}"},
        {"指标": "总订单数",          "数值": total_orders},
        {"指标": "总销量(正品)",      "数值": total_qty},
        {"指标": "总销售额(商家收入)","数值": round(total_revenue, 2)},
        {"指标": "  产品成本（正品）","数值": round(product_cost, 2)},
        {"指标": "  赠品/包装成本",   "数值": round(gift_cost, 2)},
        {"指标": "合计总成本",        "数值": round(total_cost, 2)},
        {"指标": "总毛利润",          "数值": round(total_profit, 2)},
        {"指标": "整体毛利率",        "数值": f"{avg_margin:.2%}"},
        {"指标": "平均客单价",        "数值": round(avg_order_val, 2)},
    ]

    # ── 广告费用区块（始终显示；CSV场景行自动填入，手工项留空）──────
    total_ads   = ads_df["花费"].sum() \
                  if ads_df is not None and "花费" in ads_df.columns else 0.0
    ads_revenue = ads_df["总成交金额"].sum() \
                  if ads_df is not None and "总成交金额" in ads_df.columns else 0.0
    ads_roi     = ads_revenue / total_ads if total_ads > 0 else 0
    ads_rate    = total_ads / total_revenue if total_revenue != 0 else 0

    summary_rows.append({"指标": "── 推广费用 ──", "数值": ""})

    # CSV 场景行（有广告报表且含场景列时自动填入）
    if ads_df is not None and "花费" in ads_df.columns \
            and "场景名字" in ads_df.columns:
        scene_grp = ads_df.groupby("场景名字")["花费"].sum()
        for scene, cost in scene_grp.items():
            summary_rows.append({"指标": f"  {scene}", "数值": round(cost, 2)})
    elif total_ads > 0:
        # 无场景明细（手动录入或平台报表无场景列）：插入一行汇总数值
        # 这样 reporter 的 SUM 公式才能正确包含它，不会被覆盖为 0
        plat_label = platform if platform else "广告"
        summary_rows.append({"指标": f"  {plat_label}推广费", "数值": round(total_ads, 2)})

    # 手工填写的平台营销项（橙色格，用户自行录入）
    for item in ["淘宝客", "品销宝", "品牌新享", "百亿补贴", "淘金币", "先用后付", "限时红包"]:
        summary_rows.append({"指标": f"  {item}", "数值": ""})

    summary_rows += [
        {"指标": "推广费用合计", "数值": round(total_ads, 2)},  # reporter 写 SUM 公式
        {"指标": "广告费率",     "数值": f"{ads_rate:.2%}"},
        {"指标": "广告ROI",      "数值": round(ads_roi, 2)},
        {"指标": "── 净利润 ──", "数值": ""},
        {"指标": "营销后净利润", "数值": ""},   # reporter 写公式 =总毛利润-推广费用合计
        {"指标": "净利润率",     "数值": ""},   # reporter 写公式 =营销后净利润/总销售额
    ]

    # ── 物流费用（人工填入）──────────────────────────────────────────
    summary_rows += [
        {"指标": "── 物流费用 ──",   "数值": ""},
        {"指标": "快递/物流费用",    "数值": ""},   # ← 人工填写
    ]

    # ── 平台费用（基础服务费自动算，其余手动填）────────────────────
    platform_base = round(total_revenue * 0.06, 2)   # 基础服务费 = 销售额×6%
    summary_rows += [
        {"指标": "── 平台费用 ──",          "数值": ""},
        {"指标": "  基础服务费（6%）",      "数值": platform_base},  # ← 自动
        {"指标": "  平台罚款",              "数值": ""},             # ← 人工填写
        {"指标": "  其他【客服打款】",      "数值": ""},             # ← 人工填写
        {"指标": "  类目服务费",            "数值": ""},             # ← 人工填写
        {"指标": "平台费用合计",            "数值": ""},             # ← reporter 写公式
    ]

    # ── 税费计算（自动）────────────────────────────────────────────
    total_ads_spent = (
        ads_df["花费"].sum()
        if ads_df is not None and "花费" in ads_df.columns
        else 0.0
    )
    # ── 增值税净额计算 ──────────────────────────────────────────────
    # 税率规则：
    #   慕咖品牌（含 moodycoffee）：全部 13%
    #   巴恩天然品牌：
    #     正品/赠品：蜂蜜食品 9%，苹果醋/其他 13%
    #     包材 & 非蜂蜜赠品（勺子/杯子/盒/袋等）：13%
    #   辅助服务（推广费 + 平台基础服务费）：6%
    # ─────────────────────────────────────────────────────────────
    _store_lower = store.lower()
    _is_mukka    = any(kw in _store_lower for kw in ("慕咖", "moodycoffee"))

    # 蜂蜜食品关键词（含则 9%）
    _HONEY_KW = ("蜂蜜", "蜂王浆", "花粉")
    # 辅助品/包材关键词（优先判断；含则 13%，即使名称中有"蜂蜜"字样）
    _TOOL_KW  = ("勺", "杯", "刷", "盒", "袋", "册", "贴纸", "挂耳", "快递")

    def _item_rate(name: str) -> float:
        """根据产品名称返回适用税率（仅供巴恩天然使用）"""
        n = str(name)
        if any(k in n for k in _TOOL_KW):
            return 0.13        # 辅助品/包材 → 13%
        if any(k in n for k in _HONEY_KW):
            return 0.09        # 蜂蜜食品 → 9%
        return 0.13            # 苹果醋/其他 → 13%

    def _num_col(df: pd.DataFrame, col: str) -> "pd.Series":
        if col in df.columns:
            return pd.to_numeric(df[col], errors="coerce").fillna(0.0)
        return pd.Series([0.0] * len(df), index=df.index, dtype=float)

    if _is_mukka:
        # ── 慕咖：全部 13% ──────────────────────────────────────
        vat_sales   = round(total_revenue * 0.13, 2)
        vat_product = round(product_cost  * 0.13, 2)
        vat_gift    = round(gift_cost     * 0.13, 2)
        rate_label  = "13%"
    else:
        # ── 巴恩天然：按产品名逐行判断 9% / 13% ───────────────
        real_names  = real["商品名称"] if "商品名称" in real.columns \
                      else pd.Series([""] * len(real), index=real.index)
        gift_names  = gift["商品名称"] if "商品名称" in gift.columns \
                      else pd.Series([""] * len(gift), index=gift.index)

        real_rates  = real_names.apply(_item_rate)
        gift_rates  = gift_names.apply(_item_rate)

        # 销售额按产品级收入拆分（真实发票基础）
        vat_sales   = round((_num_col(real, "商家收入") * real_rates).sum(), 2)
        vat_product = round((_num_col(real, "总成本")   * real_rates).sum(), 2)
        vat_gift    = round((_num_col(gift, "单位成本") * gift_rates).sum(), 2)
        rate_label  = "蜂蜜9%/醋类13%"

    # 推广费 + 平台基础服务费 → 现代服务 6% 进项
    vat_ads   = round((total_ads_spent + platform_base) * 0.06, 2)
    # 净增值税 = 销项 − 各进项（可为负，表示留抵税额）
    total_tax = round(vat_sales - vat_product - vat_gift - vat_ads, 2)

    summary_rows += [
        {"指标": "── 税费计算 ──",                                      "数值": ""},
        {"指标": f"  增值税销项（{rate_label}）",                        "数值": vat_sales},
        {"指标": f"  进项税：产品成本（{rate_label}）",                  "数值": -vat_product},
        {"指标": f"  进项税：赠品/包材（{rate_label}）",                 "数值": -vat_gift},
        {"指标": "  进项税：推广费+平台收费（×6%）",                     "数值": -vat_ads},
        {"指标": "合计税费",                                              "数值": total_tax},
    ]

    # ── 综合净利润（所有费用扣除后）────────────────────────────────
    summary_rows += [
        {"指标": "── 综合净利润 ──", "数值": ""},
        {"指标": "综合净利润",       "数值": ""},   # ← reporter 写公式
        {"指标": "综合净利润率",     "数值": ""},   # ← reporter 写公式
    ]

    # ── Top 10 SKU ────────────────────────────────────────────────
    top10 = real.groupby("SKU编码").agg(
        销量    = ("销量",     "sum"),
        销售额  = ("商家收入", "sum"),
        毛利润  = ("毛利润",   "sum"),
    ).reset_index().sort_values("销售额", ascending=False).head(10)
    name_map = (
        real.groupby("SKU编码")["商品名称"]
        .agg(lambda s: s.mode().iloc[0] if not s.mode().empty else s.iloc[0])
    )
    top10["商品名称"] = top10["SKU编码"].map(name_map)
    top10["毛利率"] = top10.apply(
        lambda r: r["毛利润"] / r["销售额"] if r["销售额"] != 0 else 0, axis=1
    )
    top10.insert(0, "排名", range(1, len(top10) + 1))

    spacer = pd.DataFrame([{"指标": "── Top 10 SKU（按销售额）──"}])
    result = pd.concat(
        [pd.DataFrame(summary_rows), spacer, top10],
        ignore_index=True
    )
    return result


def build_monthly_comparison(monthly_summaries: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """
    以第一个月的毛利汇总行结构为模板，各月数值按列排列。
    - 截止到 Top 10 SKU 段之前（不含SKU明细表）
    - 公式行（营销后净利润/净利润率/综合净利润/综合净利润率）由此处直接计算
    """
    if not monthly_summaries:
        return pd.DataFrame()

    # ── 取行模板（任意一个月的毛利汇总，截到 Top10 前）─────────────
    template_df = next(v for v in monthly_summaries.values() if v is not None)
    cutoff = len(template_df)
    for i, (_, row) in enumerate(template_df.iterrows()):
        if "Top 10" in str(row.get("指标", "")):
            cutoff = i
            break
    indicators = template_df["指标"].iloc[:cutoff].tolist()

    # ── 辅助：从 lookup dict 中取数值 ────────────────────────────
    def _num(lookup, key, default=0.0):
        v = lookup.get(key, "")
        if isinstance(v, (int, float)) and not (isinstance(v, float) and v != v):
            return float(v)
        try:
            s = str(v).strip()
            if s.endswith("%"):
                return float(s[:-1]) / 100
            return float(s)
        except Exception:
            return default

    rows = []
    for indicator in indicators:
        row_data = {"指标": indicator}
        for month_str, df in sorted(monthly_summaries.items()):
            label = f"{month_str[:4]}年{month_str[4:]}月"
            if df is None or "指标" not in df.columns:
                row_data[label] = ""
                continue

            lookup = df.set_index("指标")["数值"].to_dict()

            # 公式行：实时计算
            revenue     = _num(lookup, "总销售额(商家收入)")
            total_pft   = _num(lookup, "总毛利润")
            ads_total   = _num(lookup, "推广费用合计")
            tax_total   = _num(lookup, "合计税费")
            logistics   = _num(lookup, "快递/物流费用")
            plat_total  = _num(lookup, "平台费用合计")

            if indicator == "营销后净利润":
                val = round(total_pft - ads_total, 2)
            elif indicator == "净利润率":
                net = total_pft - ads_total
                val = round(net / revenue, 4) if revenue else ""
            elif indicator == "综合净利润":
                net = total_pft - ads_total
                val = round(net - logistics - plat_total - tax_total, 2)
            elif indicator == "综合净利润率":
                net = total_pft - ads_total
                comp = net - logistics - plat_total - tax_total
                val = round(comp / revenue, 4) if revenue else ""
            else:
                val = lookup.get(indicator, "")
                # 百分比字符串转浮点（Excel 格式化会显示为%）
                if isinstance(val, str) and val.endswith("%"):
                    try:
                        val = float(val[:-1]) / 100
                    except Exception:
                        pass

            row_data[label] = val
        rows.append(row_data)

    return pd.DataFrame(rows)


def _sheet_aftersale(after_orders: pd.DataFrame, after_prod: pd.DataFrame) -> pd.DataFrame:
    """售后相关销售汇总：打款=0 但状态交易成功的订单，单独列出成本损耗。"""

    # ── 订单概览 ──────────────────────────────────────────────────
    summary_rows = [
        {"指标": "说明",          "数值": "以下订单买家已全额退款，货物可能已退回，销售额为0，成本已损耗"},
        {"指标": "售后订单数",    "数值": after_orders["主订单号"].nunique()},
        {"指标": "涉及商品总数",  "数值": after_prod[after_prod["是否赠品"] == "正品"]["销量"].sum()},
        {"指标": "销售额",        "数值": 0.0},
        {"指标": "货物成本损耗",  "数值": round(after_prod[after_prod["是否赠品"] == "正品"]["总成本"].sum(), 2)},
        {"指标": "毛利润影响",    "数值": round(after_prod[after_prod["是否赠品"] == "正品"]["毛利润"].sum(), 2)},
    ]
    summary_df = pd.DataFrame(summary_rows)

    # ── 订单明细 ─────────────────────────────────────────────────
    order_cols = [c for c in [
        "主订单号", "日期", "下单时间", "订单状态", "商品数量",
        "退款金额", "商家收入", "省", "市",
    ] if c in after_orders.columns]
    order_detail = after_orders[order_cols].copy()
    order_detail = order_detail.sort_values("日期", ascending=True) if "日期" in order_detail.columns else order_detail

    # ── SKU 明细 ──────────────────────────────────────────────────
    prod_cols = [c for c in [
        "主订单号", "日期", "SKU编码", "商品名称", "是否赠品",
        "销量", "单位成本", "总成本", "毛利润",
    ] if c in after_prod.columns]
    prod_detail = after_prod[prod_cols].copy()

    # 拼接：汇总 + 空行 + 订单明细 + 空行 + SKU明细
    sep1 = pd.DataFrame([{"指标": "── 售后订单明细 ──"}])
    sep2 = pd.DataFrame([{"指标": "── 货物明细 ──"}])
    result = pd.concat(
        [summary_df, sep1, order_detail, sep2, prod_detail],
        ignore_index=True
    )
    return result
