-- Approval System Migration
-- Adds support for human-in-the-loop approval workflow

-- Add new status to ticket_status enum
ALTER TYPE ticket_status ADD VALUE IF NOT EXISTS 'awaiting_approval';

-- Approval status enum
CREATE TYPE approval_status AS ENUM (
    'pending',
    'approved',
    'rejected'
);

-- Approval requests table
CREATE TABLE approval_requests (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ticket_id UUID NOT NULL REFERENCES tickets(id) ON DELETE CASCADE,
    action_type TEXT NOT NULL,
    action_params JSONB NOT NULL,
    status approval_status NOT NULL DEFAULT 'pending',
    requested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    decided_at TIMESTAMPTZ,
    decided_by TEXT,
    decision_reason TEXT
);

-- Indexes for approval queries
CREATE INDEX idx_approval_requests_ticket_id ON approval_requests(ticket_id);
CREATE INDEX idx_approval_requests_status ON approval_requests(status);
CREATE INDEX idx_approval_requests_requested_at ON approval_requests(requested_at DESC);

-- RLS for approval_requests
ALTER TABLE approval_requests ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Service role full access on approval_requests"
    ON approval_requests FOR ALL
    USING (auth.role() = 'service_role');

-- Optional: Add channel field to tickets for multi-channel support
ALTER TABLE tickets ADD COLUMN IF NOT EXISTS channel TEXT DEFAULT 'api';
ALTER TABLE tickets ADD COLUMN IF NOT EXISTS metadata JSONB;

-- Index for channel filtering
CREATE INDEX IF NOT EXISTS idx_tickets_channel ON tickets(channel);
