from __future__ import annotations

from typing import Literal

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    tradovate_username: str = ""
    tradovate_password: SecretStr = SecretStr("")
    tradovate_device_id: str = ""
    tradovate_app_id: str = "MNQ Zone Bot"
    tradovate_app_version: str = "0.1.0"
    tradovate_cid: int = 0
    tradovate_sec: SecretStr = SecretStr("")
    tradovate_env: Literal["demo", "live"] = "demo"
    tradovate_account_id: int = 0

    webhook_secret: SecretStr = SecretStr("change-me")

    risk_per_trade_usd: float = 50.0
    mnq_point_value: float = 2.0
    max_concurrent_positions: int = 1
    max_armed_orders: int = 3
    daily_loss_limit_usd: float = 200.0

    dry_run: bool = True
    tif_override_gtc: bool = False
    # Test-only: skip all guardrail checks (session, max concurrent, max armed, daily loss).
    # Useful for hand-firing alerts outside market hours. NEVER set true in live trading.
    bypass_guardrails: bool = False

    db_path: str = "bot.db"

    # MCP-driven zone source (fallback path; webhook is now primary)
    poller_enabled: bool = False
    poll_interval_sec: int = 60
    mcp_server_cmd: str = "node src/server.js"
    mcp_server_cwd: str = "/Users/simone/Git/tradingview-mcp"
    chart_symbol_match: str = "MNQ"  # substring match on syminfo.tickerid
    chart_timeframe: str = "240"
    zone_within_points: int = 400  # MNQ: 400 pts ≈ 2% band

    @field_validator("tradovate_cid", "tradovate_account_id", mode="before")
    @classmethod
    def _empty_to_zero(cls, v):
        if v == "" or v is None:
            return 0
        return v

    host: str = "0.0.0.0"
    port: int = 8080
    log_level: str = "INFO"

    @property
    def tradovate_rest_base(self) -> str:
        return (
            "https://demo.tradovateapi.com/v1"
            if self.tradovate_env == "demo"
            else "https://live.tradovateapi.com/v1"
        )

    @property
    def tradovate_ws_url(self) -> str:
        return (
            "wss://demo.tradovateapi.com/v1/websocket"
            if self.tradovate_env == "demo"
            else "wss://live.tradovateapi.com/v1/websocket"
        )


settings = Settings()
