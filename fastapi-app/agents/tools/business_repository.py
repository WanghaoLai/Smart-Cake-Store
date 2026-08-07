"""Compatibility facade for the former mixed business repository."""

from .order import cancel_order, get_order_status
from .product import (
    build_verified_product_answer,
    check_stock,
    get_product_facts,
    recommend_cake,
    search_products,
    validate_product_answer,
)

__all__ = [
    "build_verified_product_answer",
    "cancel_order",
    "check_stock",
    "get_order_status",
    "get_product_facts",
    "recommend_cake",
    "search_products",
    "validate_product_answer",
]
