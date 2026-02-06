# Ticket Flow - Implementation Plan

## Completed Phases (1-10)

| Phase | Status | Description |
|-------|--------|-------------|
| Phase 1: Project Setup | ✅ Complete | Python project structure, dependencies |
| Phase 2: Database Layer | ✅ Complete | Supabase integration, tables, queries |
| Phase 3: Queue Layer | ✅ Complete | RabbitMQ with DLX, retry logic |
| Phase 4: API Layer | ✅ Complete | FastAPI endpoints, validation |
| Phase 5: Workflow Layer | ✅ Complete | LangGraph pipeline (classify→draft→finalize) |
| Phase 6: Worker Layer | ✅ Complete | Async worker, checkpointing, heartbeat |
| Phase 7: Observability | ✅ Complete | Logging, Prometheus metrics, tracing |
| Phase 8: Containerization | ✅ Complete | Docker, docker-compose |
| Phase 9: Testing | ✅ Complete | E2E tests, load tests |
| Phase 10: Documentation | ✅ Complete | Configuration docs, Grafana dashboard |

---

## Expansion Plan (Phases 11-15)

### Phase 11: Agentic Workflow Refactor
**Goal:** Replace fixed pipeline with intelligent ReAct agent that can take real actions

#### 11.1 Define Action Tools
Create tool functions the agent can call:

```python
# src/workflow/tools.py

@tool
def process_refund(order_id: str, amount: float, reason: str) -> dict:
    """Process a refund for a customer order."""
    # Integration with payment provider (Stripe/mock)
    pass

@tool
def reset_password(user_email: str) -> dict:
    """Send password reset email to user."""
    # Integration with auth system
    pass

@tool
def check_order_status(order_id: str) -> dict:
    """Look up current status of an order."""
    # Query orders database
    pass

@tool
def create_bug_report(title: str, description: str, priority: str) -> dict:
    """Create internal bug report for technical issues."""
    # Create ticket in bug tracking system
    pass

@tool
def escalate_to_human(reason: str, suggested_action: str) -> dict:
    """Escalate ticket to human agent for review."""
    # Flag ticket for human review
    pass

@tool
def search_knowledge_base(query: str) -> dict:
    """Search FAQ/docs for answers."""
    # Vector search or keyword search
    pass
```

#### 11.2 ReAct Agent Graph
Replace fixed pipeline with ReAct pattern:

```python
# src/workflow/agent.py

from langgraph.prebuilt import create_react_agent

tools = [
    process_refund,
    reset_password,
    check_order_status,
    create_bug_report,
    escalate_to_human,
    search_knowledge_base,
]

agent = create_react_agent(
    model=llm,
    tools=tools,
    state_modifier=system_prompt,
)
```

#### 11.3 Action Categories
| Category | Tools Available | Auto-Approve? |
|----------|----------------|---------------|
| Information | search_knowledge_base, check_order_status | Yes |
| Account | reset_password | Yes |
| Financial | process_refund | No - requires approval |
| Technical | create_bug_report | Yes |
| Escalation | escalate_to_human | Yes |

#### Files to Create/Modify:
- `src/workflow/tools.py` - Implement real tool functions
- `src/workflow/agent.py` - ReAct agent implementation
- `src/workflow/graph.py` - Update to use agent instead of fixed pipeline

---

### Phase 12: Human-in-the-Loop Approval System
**Goal:** Require human approval for sensitive actions (refunds, account changes)

#### 12.1 Database Schema
```sql
-- Add to Supabase
CREATE TABLE approval_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticket_id UUID REFERENCES tickets(id),
    action_type TEXT NOT NULL,
    action_params JSONB NOT NULL,
    status TEXT DEFAULT 'pending', -- pending, approved, rejected
    requested_at TIMESTAMPTZ DEFAULT NOW(),
    decided_at TIMESTAMPTZ,
    decided_by TEXT,
    decision_reason TEXT
);
```

#### 12.2 Approval Flow
```
Agent decides to refund
    ↓
Check: requires_approval("process_refund") → True
    ↓
Create approval_request (status=pending)
    ↓
Ticket status → "awaiting_approval"
    ↓
Human reviews in dashboard
    ↓
If approved → Execute action, continue workflow
If rejected → Agent receives rejection, adjusts response
```

#### 12.3 Interrupt Pattern
```python
# In agent graph
def should_interrupt(state: AgentState) -> bool:
    """Check if current action requires approval."""
    last_action = state.get("pending_action")
    if last_action and last_action["tool"] in REQUIRES_APPROVAL:
        return True
    return False

# Graph with interrupt
graph = create_react_agent(...)
graph = graph.compile(interrupt_before=["tools"])
```

#### Files to Create/Modify:
- `src/database/models.py` - Add ApprovalRequest model
- `src/database/queries.py` - Add approval CRUD operations
- `src/workflow/approval.py` - Approval logic and checks
- `src/api/routes/approvals.py` - Approval endpoints

---

### Phase 13: Email Ingestion
**Goal:** Accept tickets via email in addition to API

#### 13.1 Email Webhook Endpoint
```python
# src/api/routes/email.py

@router.post("/webhooks/email/inbound")
async def receive_email(request: Request):
    """
    Webhook endpoint for email provider (SendGrid/Mailgun).
    Parses inbound email and creates ticket.
    """
    payload = await request.json()

    ticket_data = {
        "subject": payload["subject"],
        "body": payload["text"] or payload["html"],
        "customer_email": payload["from"],
        "channel": "email",
        "metadata": {
            "message_id": payload["message_id"],
            "attachments": payload.get("attachments", [])
        }
    }

    ticket = await create_ticket(ticket_data)
    await queue_ticket(ticket.id)

    return {"status": "received", "ticket_id": ticket.id}
```

#### 13.2 Email Response
```python
# src/services/email.py

async def send_ticket_response(ticket_id: str, response: str):
    """Send the agent's response back via email."""
    ticket = await get_ticket(ticket_id)

    await email_client.send(
        to=ticket.customer_email,
        subject=f"Re: {ticket.subject}",
        body=response,
        reply_to=f"support+{ticket_id}@yourdomain.com"
    )
```

#### 13.3 Thread Tracking
- Parse `In-Reply-To` header to link responses to existing tickets
- Track email thread IDs in ticket metadata
- Support multi-turn email conversations

#### Files to Create:
- `src/api/routes/email.py` - Webhook endpoint
- `src/services/email.py` - Email sending service
- `src/services/email_parser.py` - Parse inbound email formats

---

### Phase 14: React Admin Dashboard
**Goal:** Web UI for monitoring tickets, approving actions, viewing metrics

#### 14.1 Tech Stack
- React 18 + TypeScript
- Vite for build
- TailwindCSS for styling
- React Query for data fetching
- React Router for navigation

#### 14.2 Dashboard Pages

**Dashboard Home** (`/`)
- Ticket counts by status (pending, processing, completed, failed)
- Recent tickets list
- Key metrics (avg response time, completion rate)

**Tickets List** (`/tickets`)
- Filterable/sortable table
- Status, channel, priority columns
- Click to view details

**Ticket Detail** (`/tickets/:id`)
- Full ticket info (subject, body, customer)
- Event timeline (all processing steps)
- Agent reasoning/actions taken
- Final response

**Approvals Queue** (`/approvals`)
- List of pending approval requests
- Action details (refund amount, user email, etc.)
- Approve/Reject buttons with reason input
- History of past decisions

**Metrics** (`/metrics`)
- Embedded Grafana iframe or custom charts
- Ticket volume over time
- Processing times
- Approval rates

#### 14.3 Project Structure
```
dashboard/
├── package.json
├── vite.config.ts
├── tsconfig.json
├── tailwind.config.js
├── index.html
├── src/
│   ├── main.tsx
│   ├── App.tsx
│   ├── api/
│   │   └── client.ts          # API client
│   ├── components/
│   │   ├── Layout.tsx
│   │   ├── Sidebar.tsx
│   │   ├── TicketCard.tsx
│   │   ├── ApprovalCard.tsx
│   │   └── StatusBadge.tsx
│   ├── pages/
│   │   ├── Dashboard.tsx
│   │   ├── Tickets.tsx
│   │   ├── TicketDetail.tsx
│   │   ├── Approvals.tsx
│   │   └── Metrics.tsx
│   └── hooks/
│       ├── useTickets.ts
│       └── useApprovals.ts
└── Dockerfile
```

#### 14.4 API Endpoints Needed
```
GET  /api/v1/dashboard/stats     - Ticket counts, metrics
GET  /api/v1/tickets             - List tickets (paginated)
GET  /api/v1/tickets/:id         - Ticket detail with events
GET  /api/v1/approvals           - Pending approvals
POST /api/v1/approvals/:id       - Approve/reject
```

---

### Phase 15: Integration Testing
**Goal:** Verify all new components work together

#### 15.1 Test Scenarios

**Agentic Workflow Tests**
- Agent correctly identifies ticket type
- Agent uses appropriate tools
- Agent generates helpful responses
- Agent escalates when uncertain

**Approval Flow Tests**
- Refund request creates approval
- Approval executes the action
- Rejection adjusts agent response
- Ticket resumes after approval

**Email Integration Tests**
- Inbound email creates ticket
- Response sent via email
- Thread tracking works
- Attachments handled

**Dashboard Tests**
- Tickets display correctly
- Approval actions work
- Real-time updates (polling/websocket)

#### 15.2 Test Files
```
tests/
├── test_agent.py          # Agent tool selection tests
├── test_approval_flow.py  # Approval system tests
├── test_email.py          # Email ingestion tests
└── test_dashboard.py      # API endpoint tests for dashboard
```

---

## Implementation Order

```
Phase 11: Agentic Workflow
    ├── 11.1 Tool definitions
    ├── 11.2 ReAct agent
    └── 11.3 Integration with existing worker
            ↓
Phase 12: Approval System
    ├── 12.1 Database schema
    ├── 12.2 Approval endpoints
    └── 12.3 Graph interrupts
            ↓
Phase 13: Email Ingestion
    ├── 13.1 Webhook endpoint
    ├── 13.2 Email parser
    └── 13.3 Response sender
            ↓
Phase 14: React Dashboard
    ├── 14.1 Project setup
    ├── 14.2 Core pages
    └── 14.3 Approval UI
            ↓
Phase 15: Integration Tests
    └── Full system validation
```

---

## Current Status

| Phase | Status | Progress |
|-------|--------|----------|
| Phase 11: Agentic Workflow | ✅ Complete | 100% |
| Phase 12: Approval System | ✅ Complete | 100% |
| Phase 13: Email Ingestion | ✅ Complete | 100% |
| Phase 14: React Dashboard | ✅ Complete | 100% |
| Phase 15: Integration Tests | ⏳ Pending | 0% |

### Completed in This Session

**Phase 11 - Agentic Workflow:**
- ✅ `src/workflow/tools.py` - 7 action tools with LangChain `@tool` decorator
- ✅ `src/workflow/agent.py` - ReAct agent with conditional tool execution
- ✅ `src/worker/processor.py` - Updated to support both agent and legacy workflow
- ✅ `src/common/config.py` - Added `use_agent_workflow` config flag

**Phase 12 - Approval System:**
- ✅ `migrations/002_approval_system.sql` - Database schema for approval_requests
- ✅ `src/db/models.py` - ApprovalRequest, ApprovalStatus models
- ✅ `src/db/repositories.py` - ApprovalRepository with CRUD operations
- ✅ `src/api/routes.py` - Approval endpoints (GET /approvals, POST /approvals/:id/decide)
- ✅ `src/api/routes.py` - Dashboard stats endpoint (GET /dashboard/stats)
- ✅ `src/api/routes.py` - Tickets list endpoint (GET /tickets with pagination)

**Phase 13 - Email Ingestion:**
- ✅ `src/api/email_routes.py` - Webhook endpoints for SendGrid, Mailgun, Postmark, and generic
- ✅ `src/services/email_parser.py` - Email parser with multi-provider support
- ✅ `src/services/email_sender.py` - Email sender with SendGrid/Mailgun/Mock backends
- ✅ `src/common/config.py` - Email provider configuration settings
- ✅ `src/api/main.py` - Registered email routes

**Phase 14 - React Admin Dashboard:**
- ✅ `dashboard/` - Complete React + TypeScript + Vite + TailwindCSS project
- ✅ `dashboard/src/api/client.ts` - API client with typed interfaces
- ✅ `dashboard/src/hooks/` - React Query hooks for tickets and approvals
- ✅ `dashboard/src/pages/Dashboard.tsx` - Stats overview with ticket counts
- ✅ `dashboard/src/pages/Tickets.tsx` - Paginated ticket list with filters
- ✅ `dashboard/src/pages/TicketDetail.tsx` - Full ticket view with timeline
- ✅ `dashboard/src/pages/Approvals.tsx` - Approval queue with approve/reject UI
- ✅ `dashboard/Dockerfile` - Production build with nginx
- ✅ `docker-compose.yml` - Dashboard service added

**Phase 14+ - Dashboard UX Improvements:**
- ✅ `dashboard/src/api/client.ts` - Added createTicket API method
- ✅ `dashboard/src/hooks/useTickets.ts` - Added useCreateTicket, auto-refresh hooks
- ✅ `dashboard/src/pages/CreateTicket.tsx` - **NEW** Ticket submission form with example templates
- ✅ `dashboard/src/components/WorkflowProgress.tsx` - **NEW** Visual workflow pipeline component
- ✅ `dashboard/src/pages/TicketDetail.tsx` - Integrated WorkflowProgress, added auto-refresh
- ✅ `dashboard/src/components/Layout.tsx` - Added highlighted "New Ticket" nav button
- ✅ `dashboard/src/App.tsx` - Added /tickets/new route

**Features Added:**
1. **Ticket Submission UI** - Create tickets from dashboard (no curl needed)
2. **Visual Workflow Panel** - Shows ticket journey: Received → Analyzing → Tools → Approval → Complete
3. **Auto-Refresh** - Updates every 3 seconds while processing
4. **Live Indicator** - Shows "Live" badge when auto-refreshing
5. **Example Tickets** - Pre-filled templates for testing different scenarios

**Next Step:** Phase 15 - Integration Tests (optional)
