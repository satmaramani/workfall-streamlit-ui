from __future__ import annotations

from config import INVENTORY_BASE_URL
from http_client import get_json


def load_inventory_products() -> tuple[list[dict], str | None]:
    result = get_json(f"{INVENTORY_BASE_URL}/api/v1/products")
    if not result["ok"]:
        return [], result["error"]
    return result["data"].get("products", []), None


def product_option_labels(products: list[dict]) -> list[str]:
    return [
        (
            f"{item['product_name']} ({item['product_id']})"
            f" | Available: {item['quantity']}"
            f" | Price: {item['unit_price']}"
        )
        for item in products
    ]


def product_option_map(products: list[dict]) -> dict[str, str]:
    return {
        item["product_id"]: (
            f"{item['product_name']} ({item['product_id']})"
            f" | Available: {item['quantity']}"
            f" | Price: {item['unit_price']}"
        )
        for item in products
    }
