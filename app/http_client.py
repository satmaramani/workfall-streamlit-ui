from __future__ import annotations

from typing import Any

import httpx


def post_json(url: str, payload: dict[str, Any], timeout: float = 15.0) -> dict[str, Any]:
    try:
        response = httpx.post(url, json=payload, timeout=timeout)
        response.raise_for_status()
        return {"ok": True, "data": response.json()}
    except Exception as exc:  # pragma: no cover
        return {"ok": False, "error": str(exc)}


def get_json(url: str, timeout: float = 10.0) -> dict[str, Any]:
    try:
        response = httpx.get(url, timeout=timeout)
        response.raise_for_status()
        return {"ok": True, "data": response.json()}
    except Exception as exc:  # pragma: no cover
        return {"ok": False, "error": str(exc)}
