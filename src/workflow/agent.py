"""
ReAct Agent for ticket processing.

This module implements an intelligent agent that can reason about customer
tickets and take appropriate actions using available tools.
"""

from typing import Annotated, Any, Sequence, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from src.common.config import get_settings
from src.common.logging import get_logger
from src.workflow.tools import get_all_tools, requires_approval

logger = get_logger(__name__)

SYSTEM_PROMPT = """You are an intelligent customer support agent. Your job is to help resolve customer support tickets efficiently and professionally.

## Your Tools

### Information Tools (query the database)
1. **query_help_articles** - Search FAQs and help documentation
   - Use `category` filter: 'account', 'orders', 'shipping', 'billing', 'technical'
   - Use `search_term` for keyword search
   - Example: For password issues, use category='account' or search_term='password'

2. **check_order_status** - Look up order details by order ID
   - Returns: status, items, tracking number, shipping info, dates
   - Order IDs look like: 'ord_12345'

3. **get_customer_history** - View customer info and past interactions
   - Accepts customer ID or email
   - Returns: customer details, tier, previous tickets, recent orders

4. **lookup_product** - Find product information
   - Search by product_id (e.g., 'prod_wh1000') or name_search

### Action Tools
5. **reset_password** - Send password reset email to customer

6. **process_refund** - Issue a refund (REQUIRES APPROVAL)
   - Always verify the order exists first using check_order_status
   - Needs: order_id, amount, reason

7. **create_bug_report** - Report technical issues to engineering
   - Creates a GitHub issue if configured
   - Set priority: 'low', 'medium', 'high', 'critical'

8. **escalate_to_human** - Transfer to human agent for complex issues

## Guidelines
1. **Query First**: Use tools to gather information before responding
2. **Verify Orders**: Always check order status before processing refunds
3. **Use Help Articles**: Search FAQs before giving generic answers
4. **Be Specific**: Include order numbers, tracking info, etc. in responses
5. **Know Your Limits**: Escalate when uncertain or when customer requests human

## Response Format
After gathering information, provide a clear, helpful response with:
- Specific details from your queries (order status, tracking, etc.)
- Any actions taken (password reset sent, refund submitted for approval)
- Next steps for the customer

Remember: You have real access to customer data, orders, and help documentation. Use it to provide personalized, accurate support."""


class AgentState(TypedDict):
    """State for the ReAct agent."""

    # Input
    ticket_id: str
    customer_id: str
    subject: str
    body: str

    # Messages for the agent
    messages: Annotated[Sequence[BaseMessage], add_messages]

    # Output
    final_response: str | None
    actions_taken: list[dict[str, Any]]

    # Control flow
    pending_approval: dict[str, Any] | None
    should_end: bool


def create_agent_graph():
    """Create the ReAct agent graph."""
    settings = get_settings()

    # Initialize LLM
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0,
        api_key=settings.openai_api_key,
        timeout=settings.llm_timeout_seconds,
        max_retries=settings.llm_max_retries,
    )

    # Bind tools to LLM
    tools = get_all_tools()
    llm_with_tools = llm.bind_tools(tools)

    # Tool node for executing tools
    tool_node = ToolNode(tools)

    def agent_node(state: AgentState) -> dict[str, Any]:
        """The reasoning node - decides what action to take."""
        logger.info(
            "agent_reasoning",
            ticket_id=state["ticket_id"],
            message_count=len(state["messages"]),
        )

        # Call LLM to decide next action
        response = llm_with_tools.invoke(state["messages"])

        # Check if LLM wants to use a tool
        if response.tool_calls:
            logger.info(
                "agent_tool_call",
                ticket_id=state["ticket_id"],
                tools=[tc["name"] for tc in response.tool_calls],
            )

            # Check if any tool requires approval
            for tool_call in response.tool_calls:
                if requires_approval(tool_call["name"]):
                    logger.info(
                        "agent_approval_required",
                        ticket_id=state["ticket_id"],
                        tool=tool_call["name"],
                        args=tool_call["args"],
                    )
                    return {
                        "messages": [response],
                        "pending_approval": {
                            "tool": tool_call["name"],
                            "args": tool_call["args"],
                            "tool_call_id": tool_call["id"],
                        },
                    }

        return {"messages": [response]}

    def should_continue(state: AgentState) -> str:
        """Determine what to do next based on the last message."""
        # Check if we're waiting for approval
        if state.get("pending_approval"):
            return "await_approval"

        # Check the last message
        last_message = state["messages"][-1]

        # If it's an AI message with tool calls, execute tools
        if isinstance(last_message, AIMessage) and last_message.tool_calls:
            return "tools"

        # Otherwise, we're done
        return "finalize"

    def finalize_node(state: AgentState) -> dict[str, Any]:
        """Extract the final response from the agent."""
        # Get the last AI message as the response
        for message in reversed(state["messages"]):
            if isinstance(message, AIMessage) and not message.tool_calls:
                final_response = message.content
                logger.info(
                    "agent_finalized",
                    ticket_id=state["ticket_id"],
                    response_length=len(final_response),
                )
                return {
                    "final_response": final_response,
                    "should_end": True,
                }

        # Fallback if no clean response found
        return {
            "final_response": "I apologize, but I was unable to process your request. A human agent will review your ticket shortly.",
            "should_end": True,
        }

    def await_approval_node(state: AgentState) -> dict[str, Any]:
        """
        Node that handles approval waiting.
        In the actual flow, this will be interrupted by the approval system.
        """
        pending = state.get("pending_approval", {})
        logger.info(
            "agent_awaiting_approval",
            ticket_id=state["ticket_id"],
            tool=pending.get("tool"),
        )

        # This will be the end of processing until approval is received
        # The approval system will resume the graph with the approval decision
        return {
            "final_response": f"Your request requires approval. A support manager will review and approve the {pending.get('tool', 'action')} shortly.",
            "should_end": True,
        }

    def tools_node(state: AgentState) -> dict[str, Any]:
        """Execute tools and track actions taken."""
        result = tool_node.invoke(state)

        # Track what actions were taken
        actions = state.get("actions_taken", [])
        last_message = state["messages"][-1]

        if isinstance(last_message, AIMessage) and last_message.tool_calls:
            for tool_call in last_message.tool_calls:
                actions.append(
                    {
                        "tool": tool_call["name"],
                        "args": tool_call["args"],
                    }
                )

        return {
            "messages": result["messages"],
            "actions_taken": actions,
        }

    # Build the graph
    workflow = StateGraph(AgentState)

    # Add nodes
    workflow.add_node("agent", agent_node)
    workflow.add_node("tools", tools_node)
    workflow.add_node("finalize", finalize_node)
    workflow.add_node("await_approval", await_approval_node)

    # Set entry point
    workflow.set_entry_point("agent")

    # Add conditional edges from agent
    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",
            "finalize": "finalize",
            "await_approval": "await_approval",
        },
    )

    # Tools loop back to agent for more reasoning
    workflow.add_edge("tools", "agent")

    # Finalize and await_approval end the graph
    workflow.add_edge("finalize", END)
    workflow.add_edge("await_approval", END)

    return workflow


def get_compiled_agent():
    """Get the compiled agent ready for execution."""
    workflow = create_agent_graph()
    return workflow.compile()


def create_initial_state(
    ticket_id: str,
    customer_id: str,
    subject: str,
    body: str,
) -> AgentState:
    """Create the initial state for processing a ticket."""
    # Format the ticket as a human message
    ticket_message = f"""## Support Ticket

**Ticket ID:** {ticket_id}
**Customer ID:** {customer_id}
**Subject:** {subject}

**Message:**
{body}

Please analyze this ticket and help resolve the customer's issue."""

    return {
        "ticket_id": ticket_id,
        "customer_id": customer_id,
        "subject": subject,
        "body": body,
        "messages": [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=ticket_message),
        ],
        "final_response": None,
        "actions_taken": [],
        "pending_approval": None,
        "should_end": False,
    }


async def process_ticket_with_agent(
    ticket_id: str,
    customer_id: str,
    subject: str,
    body: str,
) -> dict[str, Any]:
    """
    Process a ticket using the ReAct agent.

    Returns:
        A dict containing:
        - final_response: The agent's response to the customer
        - actions_taken: List of tools/actions the agent used
        - pending_approval: If not None, indicates an action awaiting approval
    """
    logger.info(
        "agent_processing_ticket",
        ticket_id=ticket_id,
        subject=subject,
    )

    # Create initial state
    initial_state = create_initial_state(
        ticket_id=ticket_id,
        customer_id=customer_id,
        subject=subject,
        body=body,
    )

    # Get compiled agent
    agent = get_compiled_agent()

    # Run the agent
    final_state = agent.invoke(initial_state)

    logger.info(
        "agent_completed",
        ticket_id=ticket_id,
        actions_taken=len(final_state.get("actions_taken", [])),
        pending_approval=final_state.get("pending_approval") is not None,
    )

    return {
        "final_response": final_state.get("final_response"),
        "actions_taken": final_state.get("actions_taken", []),
        "pending_approval": final_state.get("pending_approval"),
    }
