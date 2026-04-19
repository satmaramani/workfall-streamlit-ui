from __future__ import annotations

from typing import Any

import httpx


def _extract_error(exc: Exception) -> str:
    if isinstance(exc, httpx.HTTPStatusError):
        response = exc.response
        try:
            payload = response.json()
            if isinstance(payload, dict):
                detail = payload.get("detail")
                if isinstance(detail, str) and detail.strip():
                    return detail
        except Exception:
            pass
        return f"Request failed with status {response.status_code}."
    return str(exc)


def post_json(url: str, payload: dict[str, Any], timeout: float = 15.0) -> dict[str, Any]:
    try:
        response = httpx.post(url, json=payload, timeout=timeout)
        response.raise_for_status()
        return {"ok": True, "data": response.json()}
    except Exception as exc:  # pragma: no cover
        return {"ok": False, "error": _extract_error(exc)}


def get_json(url: str, timeout: float = 10.0) -> dict[str, Any]:
    try:
        response = httpx.get(url, timeout=timeout)
        response.raise_for_status()
        return {"ok": True, "data": response.json()}
    except Exception as exc:  # pragma: no cover
        return {"ok": False, "error": _extract_error(exc)}


def delete_json(url: str, timeout: float = 15.0) -> dict[str, Any]:
    try:
        response = httpx.delete(url, timeout=timeout)
        response.raise_for_status()
        return {"ok": True, "data": response.json()}
    except Exception as exc:  # pragma: no cover
        return {"ok": False, "error": _extract_error(exc)}
