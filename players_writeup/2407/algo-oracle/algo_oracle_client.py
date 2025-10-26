"""
轻量 API 封装：包装题目站点提供的三个接口

Base URL 常量位于文件顶部，可按需修改。

接口改为用 bytes 表示 ticket，由本模块负责 Base64 编解码：
- OracleClient.gen_ticket(level:int, name:str, stuid:str) -> bytes
- OracleClient.query_ticket(level:int, ticket:bytes) -> dict
- OracleClient.get_flag(level:int, ticket:bytes, redeem_code:str = "") -> str

返回结构：
- gen_ticket: 返回服务端生成的购票凭证（已 base64 解码后的原始字节）
- query_ticket: 返回 { 'html': str, 'fields': dict }，fields 尝试解析姓名、学号、flag、code（可能打码）、timestamp
- get_flag: 返回服务端原始 HTML 文本（或错误信息）
"""

from __future__ import annotations

import base64
import re
import typing as _t

import requests


BASE_URL = "https://prob14-ktexojnb.geekgame.pku.edu.cn/"


class APIError(Exception):
    pass


class OracleClient:
    def __init__(self, base_url: str = BASE_URL, *, timeout: int = 20, session: requests.Session | None = None) -> None:
        if not base_url.endswith("/"):
            base_url += "/"
        self.base_url = base_url
        self.timeout = timeout
        self.s = session or requests.Session()

    # ----------------------
    # Public API wrappers
    # ----------------------
    def gen_ticket(self, level: int, name: str, stuid: str) -> bytes:
        """调用 /<level>/gen-ticket 生成购票凭证，返回原始字节（已解码）。

        注意：Level 1 若传 flag 参数会被拒绝，因此此处不传该参数。
        """
        self._check_level(level)
        url = f"{self.base_url}{level}/gen-ticket"
        r = self.s.get(url, params={"name": name, "stuid": stuid}, timeout=self.timeout)
        self._raise_for_http(r)
        # 页面中在 <p>...</p> 里给出凭证
        m = re.search(rb"<p>([A-Za-z0-9+/=]{16,})</p>", r.content)
        if not m:
            raise APIError(f"gen-ticket parse failed; body startswith: {r.text[:200]!r}")
        b64s = m.group(1).decode()
        try:
            return base64.b64decode(b64s)
        except Exception as e:
            raise APIError(f"gen-ticket base64 decode failed: {e}") from e

    def query_ticket(self, level: int, ticket: bytes) -> dict:
        """调用 /<level>/query-ticket 检票。

        返回: {
          'html': 原始 HTML,
          'fields': 解析字段字典（可能缺失某些键）
        }
        """
        self._check_level(level)
        url = f"{self.base_url}{level}/query-ticket"
        ticket_b64 = base64.b64encode(ticket).decode()
        r = self.s.get(url, params={"ticket": ticket_b64}, timeout=self.timeout)
        self._raise_for_http(r)
        html = r.text
        fields = self._parse_query_fields(html)
        return {"html": html, "fields": fields}

    def get_flag(self, level: int, ticket: bytes, redeem_code: str = "") -> str:
        """调用 /<level>/getflag 领取礼品。返回原始 HTML。"""
        self._check_level(level)
        url = f"{self.base_url}{level}/getflag"
        params = {"ticket": base64.b64encode(ticket).decode()}
        if redeem_code:
            params["redeem_code"] = redeem_code
        r = self.s.get(url, params=params, timeout=self.timeout)
        self._raise_for_http(r)
        return r.text

    # ----------------------
    # Helpers
    # ----------------------
    @staticmethod
    def _raise_for_http(r: requests.Response) -> None:
        try:
            r.raise_for_status()
        except Exception as e:
            raise APIError(f"HTTP {r.status_code}: {e}") from e

    @staticmethod
    def _check_level(level: int) -> None:
        if level not in (1, 2, 3):
            raise ValueError("level must be 1, 2, or 3")

    @staticmethod
    def _parse_query_fields(html: str) -> dict:
        # 尝试解析常见字段；解析不到的不报错
        out: dict[str, _t.Any] = {}
        m = re.search(r"<b>姓名：</b>\s*(.*?)\s*</p>", html)
        if m:
            out["name"] = m.group(1)
        m = re.search(r"<b>学号：</b>\s*(\d{10})\s*</p>", html)
        if m:
            out["stuid"] = m.group(1)
        m = re.search(r"<b>需要礼品：</b>\s*(True|False)\s*</p>", html)
        if m:
            out["flag"] = (m.group(1) == "True")
        # code 可能打码；原样返回匹配到的文本
        m = re.search(r"<b>礼品兑换码：</b>\s*([A-Za-z0-9*]+)\s*</p>", html)
        if m:
            out["code"] = m.group(1)
        m = re.search(r"<b>时间戳：</b>\s*(\d+)\s*</p>", html)
        if m:
            try:
                out["timestamp"] = int(m.group(1))
            except Exception:
                out["timestamp"] = m.group(1)
        return out

    # Context manager support
    def close(self) -> None:
        try:
            self.s.close()
        except Exception:
            pass

    def __enter__(self) -> "OracleClient":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()


__all__ = ["OracleClient", "APIError", "BASE_URL"]
