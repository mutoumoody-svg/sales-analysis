"""
Wangdiantong (旺店通) Open API Client.

实现旺店通开放平台标准API客户端：
- MD5签名算法（按官方规则：参数排序 → 长度前缀拼接 → 追加appsecret → MD5）
- stock_query.php 库存查询（自动分页，无时间限制）
- 通用请求方法（可扩展其他接口）

API文档: https://open.wangdian.cn/open/apidoc/doc?path=stock_query.php
签名算法: https://open.wangdian.cn/open/guide?path=guide_signsf

注意事项:
    - stock_query.php 无调用时间限制，可随时调用
    - 不带 spec_no 时必须传 start_time/end_time，跨度 ≤30 天
    - 分页 page_size 最大100，page_no 从0开始
    - total_count 仅在 page_no=0 时返回
"""

import hashlib
import time
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlencode
import httpx


# ===== 常量 =====
WANGDIAN_API_BASE = "https://api.wangdian.cn/openapi2"
WANGDIAN_SANDBOX_BASE = "https://sandbox.wangdian.cn/openapi2"
STOCK_QUERY_PATH = "/stock_query.php"


class WangdianAPIError(Exception):
    """旺店通API调用异常."""

    def __init__(self, code: int, message: str, raw_response: Optional[dict] = None):
        self.code = code
        self.message = message
        self.raw_response = raw_response
        super().__init__(f"[旺店通API错误 {code}] {message}")


class WangdianClient:
    """旺店通开放平台API客户端.

    用法:
        client = WangdianClient(sid="xxx", appkey="xxx", appsecret="xxx")
        stocks = client.query_all_stock(start_time="2026-08-07 00:00:00", end_time="2026-08-08 00:00:00")
    """

    def __init__(
        self,
        sid: str,
        appkey: str,
        appsecret: str,
        sandbox: bool = False,
        timeout: int = 30,
    ):
        self.sid = sid
        self.appkey = appkey
        self.appsecret = appsecret
        self.base_url = WANGDIAN_SANDBOX_BASE if sandbox else WANGDIAN_API_BASE
        self.timeout = timeout

    # ===== 签名算法 =====

    def _generate_sign(self, params: Dict[str, str]) -> str:
        """生成旺店通API签名.

        算法步骤:
            1. 所有参数按键名正序排序（appsecret 不参与）
            2. 每个键值对格式化为: XX-key:XXXX-value; （最后一个不加分号）
               - XX = key 的 UTF-8 字节长度，2位补零
               - XXXX = value 的 UTF-8 字节长度，4位补零（超过4位用实际值）
            3. 拼接 appsecret 到末尾（无分隔符）
            4. MD5 取32位小写

        示例:
            params = {appkey: "test2-xx", sid: "test2", timestamp: "1470042310", ...}
            → "06-appkey:0008-test2-xx;03-sid:0005-test2;09-timestamp:0010-1470042310..."
            → MD5(str + appsecret)
        """
        sorted_keys = sorted(params.keys())
        parts = []
        for i, key in enumerate(sorted_keys):
            value = str(params[key])
            key_len = len(key.encode("utf-8"))
            val_len = len(value.encode("utf-8"))

            # key 长度: 2位补零
            key_part = f"{key_len:02d}-{key}"
            # value 长度: 4位补零，超过4位用实际值
            if val_len <= 9999:
                val_part = f"{val_len:04d}-{value}"
            else:
                val_part = f"{val_len}-{value}"

            # 最后一个参数不加分号
            if i < len(sorted_keys) - 1:
                parts.append(f"{key_part}:{val_part};")
            else:
                parts.append(f"{key_part}:{val_part}")

        sign_str = "".join(parts) + self.appsecret
        return hashlib.md5(sign_str.encode("utf-8")).hexdigest()

    # ===== 通用请求 =====

    def _request(self, path: str, biz_params: Dict[str, str]) -> Dict:
        """发送API请求.

        Args:
            path: 接口路径，如 /stock_query_all.php
            biz_params: 业务参数（不含公共参数）

        Returns:
            API响应的JSON dict
        """
        # 组装公共参数 + 业务参数
        params = {
            "sid": self.sid,
            "appkey": self.appkey,
            "timestamp": str(int(time.time())),
        }
        params.update(biz_params)

        # 生成签名
        params["sign"] = self._generate_sign(params)

        # 发送请求
        url = self.base_url + path
        try:
            resp = httpx.post(url, data=params, timeout=self.timeout)
            resp.raise_for_status()
            data = resp.json()
        except httpx.HTTPError as e:
            raise WangdianAPIError(-1, f"HTTP请求失败: {e}") from e
        except ValueError as e:
            raise WangdianAPIError(-1, f"响应JSON解析失败: {e}") from e

        # 检查业务错误码
        code = data.get("code", -1)
        if code != 0:
            message = data.get("message", "未知错误")
            raise WangdianAPIError(code, message, data)

        return data

    # ===== stock_query_all.php =====

    def query_all_stock(
        self,
        start_time: Optional[str] = None,
        end_time: Optional[str] = None,
        warehouse_no: Optional[str] = None,
        spec_no: Optional[str] = None,
        barcode: Optional[str] = None,
        page_size: int = 100,
    ) -> Tuple[List[Dict], int]:
        """全量查询库存（自动分页拉取所有数据）.

        使用 stock_query.php 接口，无调用时间限制。
        全量模式：按30天窗口分段拉取，合并去重。

        Args:
            start_time: 开始时间，格式 YYYY-MM-DD HH:MM:SS（按 modified 增量获取）
            end_time: 结束时间，格式 YYYY-MM-DD HH:MM:SS
            warehouse_no: 仓库编号（可选，传入则只查该仓库）
            spec_no: 商家编码/SKU（可选，传入则只查该SKU）
            barcode: 条形码（可选）
            page_size: 每页条数，1-100，默认100

        Returns:
            (stocks_list, total_count)
            stocks_list: 所有库存记录的列表
            total_count: 符合条件的总记录数
        """
        # 如果时间跨度超过30天，分段拉取
        if start_time and end_time:
            start_dt = datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
            end_dt = datetime.strptime(end_time, "%Y-%m-%d %H:%M:%S")
            if (end_dt - start_dt).days > 30:
                return self._query_stock_full(start_dt, end_dt, warehouse_no, spec_no, page_size)

        if not start_time or not end_time:
            now = datetime.now()
            start_time = (now - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
            end_time = now.strftime("%Y-%m-%d %H:%M:%S")

        return self._query_stock_window(start_time, end_time, warehouse_no, spec_no, page_size)

    def _query_stock_window(
        self,
        start_time: str,
        end_time: str,
        warehouse_no: Optional[str] = None,
        spec_no: Optional[str] = None,
        page_size: int = 100,
    ) -> Tuple[List[Dict], int]:
        """拉取一个时间窗口内的全部库存（自动分页）."""
        page_size = max(1, min(page_size, 100))
        all_stocks: List[Dict] = []
        total_count = 0
        page_no = 0

        while True:
            biz_params = {
                "start_time": start_time,
                "end_time": end_time,
                "page_size": str(page_size),
                "page_no": str(page_no),
                "is_deleted": "1",
                "spec_is_deleted": "0",
            }
            if warehouse_no:
                biz_params["warehouse_no"] = warehouse_no
            if spec_no:
                biz_params["spec_no"] = spec_no

            data = self._request(STOCK_QUERY_PATH, biz_params)

            if page_no == 0:
                total_count = data.get("total_count", 0)

            stocks = data.get("stocks", [])
            if not stocks:
                break

            all_stocks.extend(stocks)

            if len(all_stocks) >= total_count and total_count > 0:
                break
            if len(stocks) < page_size:
                break

            page_no += 1

        return all_stocks, total_count

    def _query_stock_full(
        self,
        start_dt: datetime,
        end_dt: datetime,
        warehouse_no: Optional[str] = None,
        spec_no: Optional[str] = None,
        page_size: int = 100,
    ) -> Tuple[List[Dict], int]:
        """全量拉取：按30天窗口分段，合并去重（按 spec_no + warehouse_no 保留最新 modified）."""
        all_rows: List[Dict] = []
        window_start = start_dt

        while window_start < end_dt:
            window_end = min(window_start + timedelta(days=30), end_dt)
            s = window_start.strftime("%Y-%m-%d %H:%M:%S")
            e = window_end.strftime("%Y-%m-%d %H:%M:%S")

            rows, _ = self._query_stock_window(s, e, warehouse_no, spec_no, page_size)
            all_rows.extend(rows)
            window_start = window_end

        if not all_rows:
            return [], 0

        # 按 modified 去重，保留最新
        seen: Dict[str, Dict] = {}
        for row in all_rows:
            key = f"{row.get('spec_no', '')}|{row.get('warehouse_no', '')}"
            if key not in seen or str(row.get("modified", "")) > str(seen[key].get("modified", "")):
                seen[key] = row

        result = list(seen.values())
        return result, len(result)

    def query_single_sku_stock(
        self, spec_no: str, warehouse_no: Optional[str] = None
    ) -> List[Dict]:
        """查询单个SKU的库存."""
        biz_params = {"spec_no": spec_no, "page_size": "100", "page_no": "0"}
        if warehouse_no:
            biz_params["warehouse_no"] = warehouse_no

        data = self._request(STOCK_QUERY_PATH, biz_params)
        return data.get("stocks", [])
