"""台北一日遊 MCP Server 與工具。"""

from __future__ import annotations

import hashlib
import os
from datetime import date as date_type, datetime

from fastmcp import FastMCP
from fastmcp.server.dependencies import get_http_headers

from database.queries import (
    find_user_id_by_mcp_token_hash,
    get_attraction_by_id,
    search_attractions_for_mcp,
    upsert_booking,
)


mcp = FastMCP("台北一日遊")
mcp_app = mcp.http_app(path="/")


def read_bearer_token() -> str | None:
    """讀取目前 MCP HTTP 請求的 Bearer Token。"""
    headers = {key.lower(): value for key, value in get_http_headers().items()}
    authorization = headers.get("authorization", "")
    prefix = "Bearer "
    if not authorization.startswith(prefix):
        return None
    token = authorization[len(prefix):].strip()
    return token or None


def authenticated_member_id() -> int | None:
    """將 Bearer Token 轉成會員編號；無效時回傳 None。"""
    token = read_bearer_token()
    if token is None:
        return None
    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()
    return find_user_id_by_mcp_token_hash(token_hash)


@mcp.tool(
    name="search_taipei_attractions",
    title="搜尋台北市景點",
    description="透過關鍵字和捷運站名搜尋台北市一日旅遊的景點",
)
async def search_taipei_attractions(keyword: str) -> dict:
    """以景點名稱或捷運站名稱搜尋景點。"""
    normalized_keyword = keyword.strip()
    if not normalized_keyword:
        return {"error": True}
    try:
        return {"data": search_attractions_for_mcp(normalized_keyword)}
    except Exception:
        return {"error": True}


@mcp.tool(
    name="reserve_attraction_trip",
    title="預定景點導覽行程",
    description="根據景點編號、日期、時間、價格，預定一個景點導覽行程",
)
async def reserve_attraction_trip(
    attraction_id: int,
    date: str,
    time: str,
    price: int,
) -> dict:
    """驗證會員 Token 與輸入後，建立或更新該會員的預訂。"""
    try:
        member_id = authenticated_member_id()
        if member_id is None:
            return {"error": True}

        booking_date = datetime.strptime(date.strip(), "%Y-%m-%d").date()
        normalized_time = time.strip().lower()
        time_aliases = {
            "上午": "morning",
            "早上": "morning",
            "morning": "morning",
            "下午": "afternoon",
            "afternoon": "afternoon",
        }
        booking_time = time_aliases.get(normalized_time)
        expected_price = {"morning": 2000, "afternoon": 2500}.get(booking_time)

        if (
            attraction_id < 1
            or booking_date < date_type.today()
            or expected_price is None
            or price != expected_price
            or get_attraction_by_id(attraction_id) is None
        ):
            return {"error": True}

        upsert_booking(member_id, attraction_id, booking_date, booking_time, price)
        public_base_url = os.getenv("PUBLIC_BASE_URL", "http://43.212.248.6:8000").rstrip("/")
        booking_url = f"{public_base_url}/booking"
        return {
            "ok": True,
            "message": f"台北導覽行程，預定成功，請到 {booking_url} 完成付款。",
        }
    except (TypeError, ValueError):
        return {"error": True}
    except Exception:
        return {"error": True}
