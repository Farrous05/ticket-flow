-- Ticket Flow Initial Schema
-- Run against Supabase PostgreSQL

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Ticket status enum
CREATE TYPE ticket_status AS ENUM (
    'pending',
    'processing',
    'completed',
    'failed_permanent'
);

-- Main tickets table
CREATE TABLE tickets (
    id UUID PRIMARY KEY,
    customer_id TEXT NOT NULL,
    subject TEXT NOT NULL,
    body TEXT NOT NULL,
    status ticket_status NOT NULL DEFAULT 'pending',
    result JSONB,
    worker_id TEXT,
    attempt_count INTEGER NOT NULL DEFAULT 0,
    version INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    last_heartbeat TIMESTAMPTZ
);

-- Indexes for common queries
CREATE INDEX idx_tickets_status ON tickets(status);
CREATE INDEX idx_tickets_customer_id ON tickets(customer_id);
CREATE INDEX idx_tickets_created_at ON tickets(created_at DESC);

-- Event types for audit trail
CREATE TABLE ticket_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ticket_id UUID NOT NULL REFERENCES tickets(id) ON DELETE CASCADE,
    event_type TEXT NOT NULL,
    step_name TEXT,
    payload JSONB,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Index for querying events by ticket
CREATE INDEX idx_ticket_events_ticket_id ON ticket_events(ticket_id);
CREATE INDEX idx_ticket_events_created_at ON ticket_events(ticket_id, created_at);

-- Workflow checkpoints for resumability
CREATE TABLE workflow_checkpoints (
    ticket_id UUID PRIMARY KEY REFERENCES tickets(id) ON DELETE CASCADE,
    state JSONB NOT NULL,
    current_step TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Function to update ticket version on update (optimistic locking helper)
CREATE OR REPLACE FUNCTION increment_ticket_version()
RETURNS TRIGGER AS $$
BEGIN
    NEW.version = OLD.version + 1;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to auto-increment version
CREATE TRIGGER ticket_version_trigger
    BEFORE UPDATE ON tickets
    FOR EACH ROW
    EXECUTE FUNCTION increment_ticket_version();

-- Row Level Security (RLS) policies for Supabase
ALTER TABLE tickets ENABLE ROW LEVEL SECURITY;
ALTER TABLE ticket_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE workflow_checkpoints ENABLE ROW LEVEL SECURITY;

-- Service role has full access (for backend services)
CREATE POLICY "Service role full access on tickets"
    ON tickets FOR ALL
    USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access on ticket_events"
    ON ticket_events FOR ALL
    USING (auth.role() = 'service_role');

CREATE POLICY "Service role full access on workflow_checkpoints"
    ON workflow_checkpoints FOR ALL
    USING (auth.role() = 'service_role');
