from langgraph.graph import END, StateGraph

from src.workflow.nodes import (
    classify_node,
    draft_node,
    extract_node,
    finalize_node,
    research_node,
    review_node,
)
from src.workflow.state import WorkflowState


def create_workflow() -> StateGraph:
    """Create the ticket processing workflow graph."""

    workflow = StateGraph(WorkflowState)

    # Add nodes
    workflow.add_node("classify", classify_node)
    workflow.add_node("extract", extract_node)
    workflow.add_node("research", research_node)
    workflow.add_node("draft", draft_node)
    workflow.add_node("review", review_node)
    workflow.add_node("finalize", finalize_node)

    # Define edges (sequential flow)
    workflow.set_entry_point("classify")
    workflow.add_edge("classify", "extract")
    workflow.add_edge("extract", "research")
    workflow.add_edge("research", "draft")
    workflow.add_edge("draft", "review")
    workflow.add_edge("review", "finalize")
    workflow.add_edge("finalize", END)

    return workflow


def get_compiled_workflow():
    """Get the compiled workflow ready for execution."""
    workflow = create_workflow()
    return workflow.compile()
