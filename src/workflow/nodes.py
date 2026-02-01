import re
from typing import Any

from langchain_openai import ChatOpenAI

from src.common.config import get_settings
from src.common.logging import get_logger
from src.workflow.state import WorkflowState
from src.workflow.tools import get_customer_history, search_knowledge_base

logger = get_logger(__name__)

settings = get_settings()

llm = ChatOpenAI(
    model="gpt-4o-mini",
    api_key=settings.openai_api_key,
    timeout=settings.llm_timeout_seconds,
)


def classify_node(state: WorkflowState) -> dict[str, Any]:
    """Classify the ticket into a category."""
    logger.info("node_classify", ticket_id=state.ticket_id)

    prompt = f"""Classify this customer support ticket into exactly one category.

Categories:
- billing: Payment issues, refunds, subscription problems
- technical: Product bugs, errors, functionality issues
- account: Login problems, password resets, account settings
- general: Questions, feedback, other inquiries

Ticket Subject: {state.subject}
Ticket Body: {state.body}

Respond with only the category name (billing, technical, account, or general)."""

    response = llm.invoke(prompt)
    classification = response.content.strip().lower()

    # Validate classification
    valid_categories = ["billing", "technical", "account", "general"]
    if classification not in valid_categories:
        classification = "general"

    logger.info("node_classify_complete", classification=classification)
    return {"classification": classification, "current_step": "classify"}


def extract_node(state: WorkflowState) -> dict[str, Any]:
    """Extract key entities from the ticket."""
    logger.info("node_extract", ticket_id=state.ticket_id)

    prompt = f"""Extract key entities from this customer support ticket.

Ticket Subject: {state.subject}
Ticket Body: {state.body}

Extract the following if present (respond with JSON):
- order_id: Any order or transaction ID mentioned
- product: Product or service name mentioned
- issue_type: Brief description of the issue type
- urgency: low, medium, or high based on tone and content

Respond with valid JSON only."""

    response = llm.invoke(prompt)

    # Parse JSON from response
    try:
        import json
        content = response.content.strip()
        # Handle markdown code blocks
        if content.startswith("```"):
            content = re.sub(r"```json?\n?", "", content)
            content = content.replace("```", "")
        entities = json.loads(content)
    except Exception:
        entities = {
            "order_id": None,
            "product": None,
            "issue_type": "unknown",
            "urgency": "medium",
        }

    logger.info("node_extract_complete", entities=entities)
    return {"entities": entities, "current_step": "extract"}


def research_node(state: WorkflowState) -> dict[str, Any]:
    """Research relevant information for the ticket."""
    logger.info("node_research", ticket_id=state.ticket_id)

    results = []

    # Search knowledge base
    query = f"{state.classification} {state.subject}"
    kb_results = search_knowledge_base(query)
    results.extend([{"source": "knowledge_base", **r} for r in kb_results])

    # Get customer history
    history = get_customer_history(state.customer_id)
    if history:
        results.append({
            "source": "customer_history",
            "previous_tickets": len(history),
            "tickets": history,
        })

    logger.info("node_research_complete", result_count=len(results))
    return {"research_results": results, "current_step": "research"}


def draft_node(state: WorkflowState) -> dict[str, Any]:
    """Generate a draft response."""
    logger.info("node_draft", ticket_id=state.ticket_id)

    research_context = ""
    if state.research_results:
        for r in state.research_results:
            if r.get("source") == "knowledge_base":
                research_context += f"- {r.get('title', '')}: {r.get('content', '')}\n"

    prompt = f"""Write a helpful customer support response for this ticket.

Category: {state.classification}
Subject: {state.subject}
Body: {state.body}

Extracted Information:
{state.entities}

Relevant Knowledge Base Articles:
{research_context}

Write a professional, empathetic response that addresses the customer's concern.
Be specific and actionable. Do not make up information."""

    response = llm.invoke(prompt)
    draft = response.content.strip()

    logger.info("node_draft_complete", draft_length=len(draft))
    return {"draft_response": draft, "current_step": "draft"}


def review_node(state: WorkflowState) -> dict[str, Any]:
    """Self-review the draft response."""
    logger.info("node_review", ticket_id=state.ticket_id)

    prompt = f"""Review this customer support response for quality and policy compliance.

Original Ticket:
Subject: {state.subject}
Body: {state.body}

Draft Response:
{state.draft_response}

Check for:
1. Does it address the customer's actual concern?
2. Is the tone professional and empathetic?
3. Are there any promises that shouldn't be made?
4. Is the information accurate based on the context provided?

Provide brief review notes (2-3 sentences) on what's good and any concerns."""

    response = llm.invoke(prompt)
    review_notes = response.content.strip()

    logger.info("node_review_complete")
    return {"review_notes": review_notes, "current_step": "review"}


def finalize_node(state: WorkflowState) -> dict[str, Any]:
    """Finalize the response."""
    logger.info("node_finalize", ticket_id=state.ticket_id)

    # If review notes indicate issues, we could refine here
    # For now, use the draft as final
    final_response = state.draft_response

    logger.info("node_finalize_complete")
    return {"final_response": final_response, "current_step": "finalize"}
