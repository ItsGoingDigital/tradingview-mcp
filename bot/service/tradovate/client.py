from __future__ import annotations

"""Tradovate REST client. Phase 3 implementation; Phase 2 only needs the symbol surface
so lifecycle.py imports cleanly. In DRY_RUN mode this module is never imported.
"""

import asyncio
import time

import httpx

from ..config import settings
from ..logging import log


class TradovateClient:
    def __init__(self) -> None:
        self._http = httpx.AsyncClient(base_url=settings.tradovate_rest_base, timeout=15.0)
        self._access_token: str | None = None
        self._expires_at: float = 0.0
        self._lock = asyncio.Lock()

    async def close(self) -> None:
        await self._http.aclose()

    async def _ensure_token(self) -> str:
        async with self._lock:
            now = time.time()
            if self._access_token and now < self._expires_at - 300:
                return self._access_token
            # If we have a token but it's close to expiry, try renew first.
            if self._access_token and now < self._expires_at:
                renewed = await self._renew()
                if renewed:
                    return self._access_token  # type: ignore[return-value]
            await self._login()
            return self._access_token  # type: ignore[return-value]

    async def _login(self) -> None:
        body = {
            "name": settings.tradovate_username,
            "password": settings.tradovate_password.get_secret_value(),
            "appId": settings.tradovate_app_id,
            "appVersion": settings.tradovate_app_version,
            "cid": settings.tradovate_cid,
            "sec": settings.tradovate_sec.get_secret_value(),
            "deviceId": settings.tradovate_device_id,
        }
        r = await self._http.post("/auth/accessTokenRequest", json=body)
        r.raise_for_status()
        data = r.json()
        self._access_token = data["accessToken"]
        # expirationTime is ISO; fall back to 75 min if missing.
        from datetime import datetime

        exp = data.get("expirationTime")
        if exp:
            self._expires_at = datetime.fromisoformat(exp.replace("Z", "+00:00")).timestamp()
        else:
            self._expires_at = time.time() + 75 * 60
        log.info("tradovate_logged_in", env=settings.tradovate_env)

    async def _renew(self) -> bool:
        if not self._access_token:
            return False
        try:
            r = await self._http.get(
                "/auth/renewAccessToken",
                headers={"Authorization": f"Bearer {self._access_token}"},
            )
            r.raise_for_status()
            data = r.json()
            self._access_token = data["accessToken"]
            from datetime import datetime

            exp = data.get("expirationTime")
            if exp:
                self._expires_at = datetime.fromisoformat(exp.replace("Z", "+00:00")).timestamp()
            else:
                self._expires_at = time.time() + 75 * 60
            return True
        except Exception:
            log.warning("token_renew_failed")
            return False

    async def _request(self, method: str, path: str, **kw) -> httpx.Response:
        token = await self._ensure_token()
        headers = kw.pop("headers", {})
        headers["Authorization"] = f"Bearer {token}"
        r = await self._http.request(method, path, headers=headers, **kw)
        if r.status_code == 401:
            # One forced re-login + retry.
            self._access_token = None
            token = await self._ensure_token()
            headers["Authorization"] = f"Bearer {token}"
            r = await self._http.request(method, path, headers=headers, **kw)
        r.raise_for_status()
        return r

    async def find_contract(self, name: str) -> dict:
        r = await self._request("GET", "/contract/find", params={"name": name})
        return r.json()

    async def place_oso(self, body: dict) -> dict:
        r = await self._request("POST", "/order/placeOSO", json=body)
        return r.json()

    async def cancel_order(self, order_id: int) -> dict:
        r = await self._request("POST", "/order/cancelOrder", json={"orderId": order_id})
        return r.json()

    async def list_orders(self) -> list[dict]:
        r = await self._request("GET", "/order/list")
        return r.json()


_singleton: TradovateClient | None = None


async def get_client() -> TradovateClient:
    global _singleton
    if _singleton is None:
        _singleton = TradovateClient()
    return _singleton
