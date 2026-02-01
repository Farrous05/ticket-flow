from typing import Any

from src.common.logging import get_logger
from src.db.client import get_supabase_client

logger = get_logger(__name__)


def search_knowledge_base(query: str) -> list[dict[str, Any]]:
    """
    Search the knowledge base for relevant information.

    In production, this would perform vector similarity search.
    For now, returns mock results.
    """
    logger.info("tool_search_kb", query=query)

    # Mock implementation - replace with actual vector search
    return [
        {
            "title": "Account Access FAQ",
            "content": "For account access issues, verify email and reset password through the portal.",
            "relevance": 0.85,
        },
        {
            "title": "Common Troubleshooting Steps",
            "content": "Clear browser cache, try incognito mode, check for service outages.",
            "relevance": 0.72,
        },
    ]


def get_customer_history(customer_id: str) -> list[dict[str, Any]]:
    """
    Fetch previous tickets for a customer.
    """
    logger.info("tool_get_customer_history", customer_id=customer_id)

    try:
        client = get_supabase_client()
        result = (
            client.table("tickets")
            .select("id, subject, status, created_at")
            .eq("customer_id", customer_id)
            .order("created_at", desc=True)
            .limit(5)
            .execute()
        )
        return result.data
    except Exception as e:
        logger.error("tool_get_customer_history_error", error=str(e))
        return []


def get_order_details(order_id: str) -> dict[str, Any] | None:
    """
    Fetch order details by order ID.

    In production, this would query an orders table or external system.
    For now, returns mock data.
    """
    logger.info("tool_get_order_details", order_id=order_id)

    # Mock implementation - replace with actual order lookup
    if order_id:
        return {
            "order_id": order_id,
            "status": "delivered",
            "total": 99.99,
            "items": ["Product A", "Product B"],
            "created_at": "2024-01-15T10:30:00Z",
        }
    return None
