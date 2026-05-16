from __future__ import annotations

import hashlib
import hmac

from .config import settings


def verify_signature(body: bytes, signature: str | None) -> bool:
    if not signature:
        return False
    secret = settings.webhook_secret.get_secret_value().encode()
    expected = hmac.new(secret, body, hashlib.sha256).hexdigest()
    # Constant-time compare; tolerate "sha256=..." prefix.
    candidate = signature.removeprefix("sha256=")
    return hmac.compare_digest(expected, candidate)


def verify_payload_secret(payload_secret: str) -> bool:
    """Fallback when TradingView can't send custom headers: secret is embedded in the JSON body."""
    return hmac.compare_digest(payload_secret, settings.webhook_secret.get_secret_value())
