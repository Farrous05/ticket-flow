const API_BASE = '/api'

export interface Ticket {
  id: string
  customer_id: string
  subject: string
  body: string
  status: 'pending' | 'processing' | 'awaiting_approval' | 'completed' | 'failed_permanent'
  result: Record<string, unknown> | null
  attempt_count: number
  created_at: string
  started_at: string | null
  completed_at: string | null
  channel: string | null
  metadata: Record<string, unknown> | null
}

export interface TicketEvent {
  id: string
  event_type: string
  step_name: string | null
  payload: Record<string, unknown> | null
  created_at: string
}

export interface ApprovalRequest {
  id: string
  ticket_id: string
  action_type: string
  action_params: Record<string, unknown>
  status: 'pending' | 'approved' | 'rejected'
  requested_at: string
  decided_at: string | null
  decided_by: string | null
  decision_reason: string | null
}

export interface DashboardStats {
  total_tickets: number
  pending_tickets: number
  processing_tickets: number
  awaiting_approval_tickets: number
  completed_tickets: number
  failed_tickets: number
  pending_approvals: number
}

export interface CreateTicketRequest {
  customer_id: string
  subject: string
  body: string
}

export interface CreateTicketResponse {
  ticket_id: string
  status: string
}

export interface TicketListResponse {
  tickets: Ticket[]
  total: number
  page: number
  page_size: number
}

async function fetchApi<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }))
    throw new Error(error.detail || `HTTP ${response.status}`)
  }

  return response.json()
}

export const api = {
  // Dashboard
  getStats: () => fetchApi<DashboardStats>('/dashboard/stats'),

  // Tickets
  listTickets: (page = 1, pageSize = 20, status?: string) => {
    const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) })
    if (status) params.set('status', status)
    return fetchApi<TicketListResponse>(`/tickets?${params}`)
  },

  getTicket: (id: string) => fetchApi<Ticket>(`/tickets/${id}`),

  getTicketEvents: (id: string) => fetchApi<TicketEvent[]>(`/tickets/${id}/events`),

  createTicket: (data: CreateTicketRequest) =>
    fetchApi<CreateTicketResponse>('/tickets', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  // Approvals
  listApprovals: () => fetchApi<ApprovalRequest[]>('/approvals'),

  getApproval: (id: string) => fetchApi<ApprovalRequest>(`/approvals/${id}`),

  decideApproval: (id: string, approved: boolean, decidedBy: string, reason?: string) =>
    fetchApi<{ approval_id: string; status: string; action_executed: boolean; message: string }>(
      `/approvals/${id}/decide`,
      {
        method: 'POST',
        body: JSON.stringify({ approved, decided_by: decidedBy, reason }),
      }
    ),
}
