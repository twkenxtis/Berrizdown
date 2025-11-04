import asyncio
import uuid
from typing import Any

import httpx
from httpx import Response
from pydantic import BaseModel

from berrizdown.static.color import Color
from berrizdown.unit.__init__ import USERAGENT
from berrizdown.unit.handle.handle_log import setup_logging

logger = setup_logging("httpx_login_unban", "magenta")

_session: httpx.AsyncClient | None = None


class RequestData(BaseModel):
    data: dict[str, Any]


class Request:
    cookies: dict[str, str] = {
        "pcid": str(uuid.uuid4()),
        "pacode": "fanplatf::app:android:phone",
        "__T_": "1",
        "__T_SECURE": "1",
    }

    headers: dict[str, str] = {
        "user-agent": f"{USERAGENT}",
        "accept": "application/json",
        "referer": "https://berriz.in/",
    }

    def __init__(self):
        self.retry_http_status: set[int] = frozenset({400, 401, 403, 500, 502, 503, 504})

    def get_session(self) -> httpx.AsyncClient:
        global _session
        if _session is None:
            _session = httpx.AsyncClient(http2=True, timeout=13, verify=True)
        return _session

    async def close_session(self):
        global _session
        if _session is not None:
            await _session.aclose()
            await asyncio.sleep(0.250)
            _session = None

    async def post(self, url: str, json_data: dict[str, Any] = None) -> httpx.Response:
        # Validate json_data with Pydantic if provided
        if json_data is not None:
            try:
                validated_data = RequestData(data=json_data).data
            except ValueError as e:
                logger.error(f"Invalid JSON data: {e}")
                return None
        else:
            validated_data = None

        attempt: int = 0
        while attempt < 2:
            try:
                session = self.get_session()
                response: httpx.Response = await session.post(
                    url,
                    cookies=Request.cookies,
                    headers=Request.headers,
                    json=validated_data,
                )
                if response.status_code in self.retry_http_status:
                    logger.info(f"Retryable server error: {response.text}")
                    raise httpx.HTTPStatusError(
                        f"Retryable server error: {response.status_code}",
                        request=response.request,
                        response=response,
                    )
                return response
            except httpx.HTTPStatusError as e:
                if e.response is not None:
                    logger.warning(f"HTTP server error: {e.response.status_code}, retry {attempt + 1}/{2}")
                else:
                    logger.error(f"HTTP error for {url}: {e} {Color.bg('gold')}{response}{Color.reset()}")
                    return None
            attempt += 1
            sleep: float = min(2.0, 0.5 * (2**attempt))
            await asyncio.sleep(sleep)
        logger.error(f"Retry exceeded for {url}")
        return None

    async def get(self, url: str, p: dict[str, Any]) -> httpx.Response:
        attempt: int = 0
        while attempt < 2:
            try:
                session = self.get_session()
                response: httpx.Response = await session.get(
                    url,
                    params=p,
                    cookies=Request.cookies,
                    headers=Request.headers,
                )
                if response.status_code in self.retry_http_status:
                    logger.info(f"Retryable server error: {response.text}")
                    raise httpx.HTTPStatusError(
                        f"Retryable server error: {response.status_code}",
                        request=response.request,
                        response=response,
                    )
                return response
            except httpx.HTTPStatusError as e:
                if e.response is not None:
                    logger.warning(f"HTTP server error: {e.response.status_code}, retry {attempt + 1}/{3}")
                else:
                    logger.error(f"HTTP error for {url}: {e} {Color.bg('gold')}{response}{Color.reset()}")
                    return None
            attempt += 1
            sleep: float = min(2.0, 0.5 * (2**attempt))
            await asyncio.sleep(sleep)
        logger.error(f"Retry exceeded for {url}")
        return None

    async def put(self, url: str, json_data: dict[str, Any]) -> Response:
        """發送異步 PUT 請求"""
        # Validate json_data with Pydantic
        try:
            validated_data = RequestData(data=json_data).data
        except ValueError as e:
            logger.error(f"Invalid JSON data: {e}")
            return None

        attempt: int = 0
        while attempt < 3:
            try:
                session = self.get_session()
                response: httpx.Response = await session.put(
                    url,
                    cookies=Request.cookies,
                    headers=Request.headers,
                    json=validated_data,
                )
                if response.status_code in self.retry_http_status:
                    raise httpx.HTTPStatusError(
                        f"Retryable server error: {response.status_code}",
                        request=response.request,
                        response=response,
                    )
                return response
            except httpx.HTTPStatusError as e:
                if e.response is not None:
                    logger.warning(f"HTTP server error: {e.response.status_code}, retry {attempt + 1}/{3}")
                else:
                    logger.error(f"HTTP error for {url}: {e} {Color.bg('gold')}{response}{Color.reset()}")
                    return None
            attempt += 1
            sleep: float = min(2.0, 0.5 * (2**attempt))
            await asyncio.sleep(sleep)
        logger.error(f"Retry exceeded for {url}")
        return None
