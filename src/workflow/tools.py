"""
Agent tools for the ticket processing workflow.

These tools allow the AI agent to take real actions like querying databases,
processing refunds, creating bug reports, and more.
"""

from typing import Any
from uuid import uuid4

from langchain_core.tools import tool

from src.common.logging import get_logger
from src.db.client import get_supabase_client

logger = get_logger(__name__)


# --- Information Tools ---


@tool
def query_help_articles(
    category: str | None = None,
    search_term: str | None = None
) -> dict[str, Any]:
    """
    Search the help articles and FAQ database.

    Use this tool when you need to find documentation, FAQs, or help articles
    to answer a customer's question. You can filter by category or search by term.

    Args:
        category: Optional category filter ('account', 'orders', 'technical', 'billing', 'shipping')
        search_term: Optional text to search for in article titles and content

    Returns:
        A dict with 'articles' containing relevant help articles.
    """
    logger.info("tool_query_help_articles", category=category, search_term=search_term)

    try:
        client = get_supabase_client()
        query = client.table("help_articles").select("id, title, content, category, keywords")

        # Apply category filter if provided
        if category:
            query = query.eq("category", category)

        # Apply text search if provided
        if search_term:
            # Search in title and content using ilike
            query = query.or_(
                f"title.ilike.%{search_term}%,content.ilike.%{search_term}%"
            )

        result = query.limit(5).execute()

        articles = [
            {
                "title": article["title"],
                "content": article["content"],
                "category": article["category"],
            }
            for article in result.data
        ]

        return {
            "success": True,
            "articles": articles,
            "count": len(articles),
            "category_filter": category,
            "search_term": search_term,
        }

    except Exception as e:
        logger.error("tool_query_help_articles_error", error=str(e))
        return {"success": False, "error": str(e), "articles": []}


@tool
def check_order_status(order_id: str) -> dict[str, Any]:
    """
    Look up the current status of a customer order from the database.

    Use this tool when a customer asks about their order status, shipping,
    or delivery information.

    Args:
        order_id: The order ID to look up (e.g., 'ord_12345').

    Returns:
        A dict with order details including status, items, tracking, and dates.
    """
    logger.info("tool_check_order_status", order_id=order_id)

    if not order_id:
        return {"success": False, "error": "Order ID is required"}

    try:
        client = get_supabase_client()

        # Get order with customer info
        order_result = client.table("orders").select(
            "*, customers(id, name, email, tier)"
        ).eq("id", order_id).execute()

        if not order_result.data:
            return {
                "success": False,
                "error": f"Order {order_id} not found",
                "order": None
            }

        order = order_result.data[0]

        # Get order items
        items_result = client.table("order_items").select(
            "product_name, quantity, unit_price, subtotal"
        ).eq("order_id", order_id).execute()

        items = [
            {
                "name": item["product_name"],
                "quantity": item["quantity"],
                "price": float(item["unit_price"]),
                "subtotal": float(item["subtotal"])
            }
            for item in items_result.data
        ]

        return {
            "success": True,
            "order": {
                "order_id": order["id"],
                "status": order["status"],
                "total": float(order["total"]),
                "items": items,
                "customer": order.get("customers"),
                "tracking_number": order.get("tracking_number"),
                "carrier": order.get("carrier"),
                "estimated_delivery": order.get("estimated_delivery"),
                "shipping_address": order.get("shipping_address"),
                "created_at": order["created_at"],
                "shipped_at": order.get("shipped_at"),
                "delivered_at": order.get("delivered_at"),
            },
        }

    except Exception as e:
        logger.error("tool_check_order_status_error", error=str(e))
        return {"success": False, "error": str(e), "order": None}


@tool
def get_customer_history(customer_id: str) -> dict[str, Any]:
    """
    Fetch complete customer information including orders and support history.

    Use this tool to understand a customer's full history for context-aware support.

    Args:
        customer_id: The customer ID or email to look up.

    Returns:
        A dict with customer details, order history, and previous tickets.
    """
    logger.info("tool_get_customer_history", customer_id=customer_id)

    try:
        client = get_supabase_client()

        # Try to find customer by ID or email
        customer_result = client.table("customers").select("*").or_(
            f"id.eq.{customer_id},email.eq.{customer_id}"
        ).execute()

        customer = customer_result.data[0] if customer_result.data else None

        # Get previous tickets
        tickets_result = (
            client.table("tickets")
            .select("id, subject, status, created_at")
            .eq("customer_id", customer_id)
            .order("created_at", desc=True)
            .limit(5)
            .execute()
        )

        # Get recent orders if customer found
        orders = []
        if customer:
            orders_result = (
                client.table("orders")
                .select("id, status, total, created_at")
                .eq("customer_id", customer["id"])
                .order("created_at", desc=True)
                .limit(5)
                .execute()
            )
            orders = [
                {
                    "order_id": o["id"],
                    "status": o["status"],
                    "total": float(o["total"]),
                    "created_at": o["created_at"]
                }
                for o in orders_result.data
            ]

        return {
            "success": True,
            "customer": {
                "id": customer["id"] if customer else customer_id,
                "name": customer["name"] if customer else None,
                "email": customer["email"] if customer else None,
                "tier": customer["tier"] if customer else "unknown",
                "lifetime_value": float(customer["lifetime_value"]) if customer else 0,
            } if customer else None,
            "tickets": tickets_result.data,
            "orders": orders,
            "customer_id": customer_id,
        }

    except Exception as e:
        logger.error("tool_get_customer_history_error", error=str(e))
        return {"success": False, "error": str(e), "customer": None, "tickets": [], "orders": []}


@tool
def lookup_product(
    product_id: str | None = None,
    name_search: str | None = None
) -> dict[str, Any]:
    """
    Look up product information by ID or name.

    Use this tool when you need details about a specific product mentioned
    by a customer, such as price, availability, or description.

    Args:
        product_id: The product ID to look up (e.g., 'prod_wh1000')
        name_search: Search term to find products by name

    Returns:
        A dict with product details.
    """
    logger.info("tool_lookup_product", product_id=product_id, name_search=name_search)

    if not product_id and not name_search:
        return {"success": False, "error": "Either product_id or name_search is required"}

    try:
        client = get_supabase_client()
        query = client.table("products").select("*")

        if product_id:
            query = query.eq("id", product_id)
        elif name_search:
            query = query.ilike("name", f"%{name_search}%")

        result = query.limit(5).execute()

        if not result.data:
            return {
                "success": False,
                "error": f"No products found",
                "products": []
            }

        products = [
            {
                "id": p["id"],
                "name": p["name"],
                "description": p.get("description"),
                "price": float(p["price"]),
                "category": p.get("category"),
                "in_stock": p.get("in_stock", True)
            }
            for p in result.data
        ]

        return {
            "success": True,
            "products": products,
            "count": len(products)
        }

    except Exception as e:
        logger.error("tool_lookup_product_error", error=str(e))
        return {"success": False, "error": str(e), "products": []}


# --- Account Tools ---


@tool
def reset_password(user_email: str) -> dict[str, Any]:
    """
    Send a password reset email to the user.

    Use this tool when a customer cannot log in or has forgotten their password.
    This will send an email with a secure reset link.

    Args:
        user_email: The email address of the user who needs a password reset.

    Returns:
        A dict confirming the reset email was sent.
    """
    logger.info("tool_reset_password", user_email=user_email)

    if not user_email or "@" not in user_email:
        return {"success": False, "error": "Valid email address is required"}

    # Mock implementation - in production, integrate with auth system
    reset_token = str(uuid4())[:8]

    logger.info(
        "password_reset_initiated",
        user_email=user_email,
        reset_token_prefix=reset_token[:4],
    )

    return {
        "success": True,
        "message": f"Password reset email sent to {user_email}",
        "email": user_email,
        "expires_in": "24 hours",
    }


# --- Financial Tools (Requires Approval) ---


@tool
def process_refund(order_id: str, amount: float, reason: str) -> dict[str, Any]:
    """
    Process a refund for a customer order.

    IMPORTANT: This action requires human approval before execution.
    Use this tool when a customer requests a refund for a valid reason
    such as defective product, wrong item, or service issue.

    Args:
        order_id: The order ID to refund.
        amount: The refund amount in dollars.
        reason: The reason for the refund.

    Returns:
        A dict with the refund status and confirmation details.
    """
    logger.info(
        "tool_process_refund",
        order_id=order_id,
        amount=amount,
        reason=reason,
    )

    if not order_id:
        return {"success": False, "error": "Order ID is required"}
    if amount <= 0:
        return {"success": False, "error": "Refund amount must be positive"}
    if not reason:
        return {"success": False, "error": "Refund reason is required"}

    # Verify the order exists
    try:
        client = get_supabase_client()
        order_result = client.table("orders").select("id, total, status").eq("id", order_id).execute()

        if not order_result.data:
            return {"success": False, "error": f"Order {order_id} not found"}

        order = order_result.data[0]
        if amount > float(order["total"]):
            return {"success": False, "error": f"Refund amount exceeds order total of ${order['total']}"}

    except Exception as e:
        logger.warning("order_verification_failed", error=str(e))
        # Continue with refund even if verification fails

    # Mock implementation - in production, integrate with Stripe or payment provider
    refund_id = f"ref_{uuid4().hex[:12]}"

    logger.info(
        "refund_processed",
        order_id=order_id,
        amount=amount,
        refund_id=refund_id,
    )

    return {
        "success": True,
        "refund_id": refund_id,
        "order_id": order_id,
        "amount": amount,
        "reason": reason,
        "status": "processed",
        "message": f"Refund of ${amount:.2f} processed for order {order_id}",
    }


# --- Technical Tools ---


@tool
def create_bug_report(
    title: str, description: str, priority: str = "medium"
) -> dict[str, Any]:
    """
    Create an internal bug report for technical issues.

    Use this tool when a customer reports a technical problem, bug, or
    system error that needs to be investigated by the engineering team.
    If GitHub is configured, this creates a real GitHub issue.

    Args:
        title: Brief title describing the bug.
        description: Detailed description of the issue including steps to reproduce.
        priority: Priority level - 'low', 'medium', 'high', or 'critical'.

    Returns:
        A dict with the created bug report details.
    """
    logger.info(
        "tool_create_bug_report",
        title=title,
        priority=priority,
    )

    if not title:
        return {"success": False, "error": "Bug title is required"}
    if not description:
        return {"success": False, "error": "Bug description is required"}
    if priority not in ["low", "medium", "high", "critical"]:
        return {"success": False, "error": "Invalid priority level"}

    # Try to create GitHub issue if configured
    try:
        from src.services.github import create_github_issue
        result = create_github_issue(title, description, priority)

        if result.get("success"):
            return {
                "success": True,
                "issue_number": result.get("issue_number"),
                "issue_url": result.get("issue_url"),
                "title": title,
                "priority": priority,
                "status": "open",
                "message": f"Bug report created: {result.get('issue_url')}",
            }
    except Exception as e:
        logger.warning("github_integration_failed", error=str(e))

    # Fallback to local ID if GitHub not configured or fails
    bug_id = f"BUG-{uuid4().hex[:6].upper()}"

    logger.info(
        "bug_report_created",
        bug_id=bug_id,
        title=title,
        priority=priority,
    )

    return {
        "success": True,
        "bug_id": bug_id,
        "title": title,
        "description": description,
        "priority": priority,
        "status": "open",
        "message": f"Bug report {bug_id} created and assigned to engineering team",
    }


# --- Escalation Tools ---


@tool
def escalate_to_human(reason: str, suggested_action: str) -> dict[str, Any]:
    """
    Escalate the ticket to a human support agent for review.

    Use this tool when:
    - The issue is too complex to resolve automatically
    - The customer explicitly requests to speak with a human
    - You're uncertain about the correct action to take
    - The situation requires empathy or judgment beyond your capabilities

    Args:
        reason: Why this ticket needs human review.
        suggested_action: Your recommendation for what the human agent should do.

    Returns:
        A dict confirming the escalation.
    """
    logger.info(
        "tool_escalate_to_human",
        reason=reason,
        suggested_action=suggested_action,
    )

    if not reason:
        return {"success": False, "error": "Escalation reason is required"}

    escalation_id = f"ESC-{uuid4().hex[:6].upper()}"

    logger.info(
        "ticket_escalated",
        escalation_id=escalation_id,
        reason=reason,
    )

    return {
        "success": True,
        "escalation_id": escalation_id,
        "reason": reason,
        "suggested_action": suggested_action,
        "status": "pending_human_review",
        "message": "Ticket has been escalated to a human support agent",
    }


# --- Tool Registry ---

# Tools that can execute automatically
AUTO_APPROVE_TOOLS = [
    "query_help_articles",
    "check_order_status",
    "get_customer_history",
    "lookup_product",
    "reset_password",
    "create_bug_report",
    "escalate_to_human",
]

# Tools that require human approval before execution
REQUIRES_APPROVAL_TOOLS = [
    "process_refund",
]

# All available tools for the agent
ALL_TOOLS = [
    query_help_articles,
    check_order_status,
    get_customer_history,
    lookup_product,
    reset_password,
    process_refund,
    create_bug_report,
    escalate_to_human,
]


def get_all_tools() -> list:
    """Get all tools available to the agent."""
    return ALL_TOOLS


def requires_approval(tool_name: str) -> bool:
    """Check if a tool requires human approval."""
    return tool_name in REQUIRES_APPROVAL_TOOLS
