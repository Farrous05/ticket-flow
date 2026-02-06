import { TicketEvent } from '../api/client'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { cn } from '@/lib/utils'
import {
  CheckCircle2,
  Circle,
  Loader2,
  Inbox,
  Brain,
  Wrench,
  ShieldCheck,
  Flag,
  XCircle,
  Radio
} from 'lucide-react'

interface ActionTaken {
  tool: string
  args?: Record<string, unknown>
}

interface WorkflowProgressProps {
  status: string
  events: TicketEvent[]
  actionsTaken?: ActionTaken[]
  isRefreshing?: boolean
}

type StageStatus = 'pending' | 'active' | 'completed' | 'failed'

interface Stage {
  id: string
  label: string
  description: string
  status: StageStatus
  timestamp?: string
  icon: React.ComponentType<{ className?: string }>
}

function getStages(status: string, events: TicketEvent[]): Stage[] {
  // Extract step names and timestamps from events
  const stepEvents = events.filter((e) => e.event_type === 'step_complete')
  const stepNames = stepEvents.map((e) => e.step_name)

  // Get timestamps for each step
  const getTimestamp = (stepName: string) => {
    const event = events.find(e => e.step_name === stepName || e.event_type === stepName)
    return event?.created_at
  }

  const hasAgent = stepNames.includes('agent')
  const hasTools = stepNames.includes('tools')
  const hasFinalize = stepNames.includes('finalize')

  // Base stages
  const stages: Stage[] = [
    {
      id: 'received',
      label: 'Received',
      description: 'Ticket ingested successfully',
      status: 'completed',
      icon: Inbox,
      timestamp: events[0]?.created_at
    },
    {
      id: 'agent',
      label: 'Analyzing',
      description: 'AI agent analyzing your request',
      status: 'pending',
      icon: Brain
    },
    {
      id: 'tools',
      label: 'Executing Tools',
      description: 'Running automated actions',
      status: 'pending',
      icon: Wrench
    },
    {
      id: 'approval',
      label: 'Approval',
      description: 'Awaiting human review',
      status: 'pending',
      icon: ShieldCheck
    },
    {
      id: 'complete',
      label: 'Complete',
      description: 'Request fulfilled',
      status: 'pending',
      icon: Flag
    },
  ]

  // Update based on ticket status
  if (status === 'pending') {
    stages[0].status = 'completed'
    stages[1].status = 'pending'
  } else if (status === 'processing') {
    stages[0].status = 'completed'

    if (hasFinalize) {
      stages[1].status = 'completed'
      stages[1].timestamp = getTimestamp('agent')
      stages[2].status = hasTools ? 'completed' : 'pending'
      if (hasTools) stages[2].timestamp = getTimestamp('tools')
      stages[4].status = 'active'
      stages[4].description = 'Generating final response...'
    } else if (hasTools) {
      stages[1].status = 'completed'
      stages[1].timestamp = getTimestamp('agent')
      stages[2].status = 'active'
      stages[2].description = 'Running automated actions...'
    } else if (hasAgent) {
      stages[1].status = 'active'
      stages[1].description = 'Agent is thinking...'
    } else {
      stages[1].status = 'active'
      stages[1].description = 'Starting analysis...'
    }
  } else if (status === 'awaiting_approval') {
    stages[0].status = 'completed'
    stages[1].status = 'completed'
    stages[1].timestamp = getTimestamp('agent')
    stages[2].status = hasTools ? 'completed' : 'pending'
    if (hasTools) stages[2].timestamp = getTimestamp('tools')
    stages[3].status = 'active'
    stages[3].description = 'Waiting for human approval'
  } else if (status === 'completed') {
    stages.forEach((stage, i) => {
      stage.status = 'completed'
      if (i === 1) stage.timestamp = getTimestamp('agent')
      if (i === 2 && hasTools) stage.timestamp = getTimestamp('tools')
      if (i === 4) stage.timestamp = getTimestamp('finalize')
    })
    stages[4].description = 'Request completed successfully'
  } else if (status === 'failed_permanent') {
    stages[0].status = 'completed'
    if (hasAgent) {
      stages[1].status = 'completed'
      stages[1].timestamp = getTimestamp('agent')
    }
    if (hasTools) {
      stages[2].status = 'completed'
      stages[2].timestamp = getTimestamp('tools')
    }
    // Mark the next pending stage as failed
    const nextPending = stages.find(s => s.status === 'pending')
    if (nextPending) {
      nextPending.status = 'failed'
      nextPending.description = 'Processing failed'
    }
  }

  return stages
}

function formatTime(dateString?: string): string {
  if (!dateString) return ''
  const date = new Date(dateString)
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

function TimelineNode({ stage, isLast, actionsTaken }: {
  stage: Stage
  isLast: boolean
  actionsTaken?: ActionTaken[]
}) {

  const getNodeStyles = () => {
    switch (stage.status) {
      case 'completed':
        return 'bg-green-500 text-white border-green-500'
      case 'active':
        return 'bg-primary text-primary-foreground border-primary'
      case 'failed':
        return 'bg-destructive text-destructive-foreground border-destructive'
      default:
        return 'bg-muted text-muted-foreground border-muted'
    }
  }

  const getLineStyles = () => {
    switch (stage.status) {
      case 'completed':
        return 'bg-green-500'
      case 'active':
        return 'bg-gradient-to-b from-green-500 to-primary'
      default:
        return 'bg-border'
    }
  }

  const showTools = stage.id === 'tools' && actionsTaken && actionsTaken.length > 0

  return (
    <div className="flex gap-4">
      {/* Timeline indicator */}
      <div className="flex flex-col items-center">
        <div
          className={cn(
            'w-10 h-10 rounded-full border-2 flex items-center justify-center transition-all',
            getNodeStyles()
          )}
        >
          {stage.status === 'completed' ? (
            <CheckCircle2 className="h-5 w-5" />
          ) : stage.status === 'active' ? (
            <Loader2 className="h-5 w-5 animate-spin" />
          ) : stage.status === 'failed' ? (
            <XCircle className="h-5 w-5" />
          ) : (
            <Circle className="h-5 w-5" />
          )}
        </div>
        {!isLast && (
          <div className={cn('w-0.5 flex-1 min-h-[40px]', getLineStyles())} />
        )}
      </div>

      {/* Content */}
      <div className="flex-1 pb-8">
        <div className="flex items-start justify-between">
          <div>
            <div className="flex items-center gap-2">
              <h4 className={cn(
                'font-medium',
                stage.status === 'pending' && 'text-muted-foreground'
              )}>
                {stage.label}
              </h4>
              {stage.status === 'active' && (
                <Badge variant="default" className="text-xs">
                  In Progress
                </Badge>
              )}
              {stage.status === 'failed' && (
                <Badge variant="destructive" className="text-xs">
                  Failed
                </Badge>
              )}
            </div>
            <p className={cn(
              'text-sm mt-0.5',
              stage.status === 'pending' ? 'text-muted-foreground/60' : 'text-muted-foreground'
            )}>
              {stage.description}
            </p>
          </div>
          {stage.timestamp && (
            <span className="text-xs text-muted-foreground font-mono">
              {formatTime(stage.timestamp)}
            </span>
          )}
        </div>

        {/* Nested tool calls for tools stage */}
        {showTools && (
          <div className="mt-3 space-y-2 pl-2 border-l-2 border-muted ml-2">
            {actionsTaken.map((action, i) => (
              <div key={i} className="flex items-center gap-2 pl-3">
                <CheckCircle2 className="h-3.5 w-3.5 text-green-500 shrink-0" />
                <Badge variant="secondary" className="text-xs font-normal">
                  {action.tool.replace(/_/g, ' ')}
                </Badge>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export function WorkflowProgress({
  status,
  events,
  actionsTaken,
  isRefreshing,
}: WorkflowProgressProps) {
  const stages = getStages(status, events)
  const isProcessing = status === 'pending' || status === 'processing'
  const isFailed = status === 'failed_permanent'

  return (
    <Card>
      <CardHeader className="pb-4">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base flex items-center gap-2">
            <Wrench className="h-4 w-4" />
            Workflow Progress
          </CardTitle>
          {isRefreshing && isProcessing && (
            <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200">
              <Radio className="h-3 w-3 mr-1 animate-pulse" />
              Live
            </Badge>
          )}
        </div>
      </CardHeader>

      <CardContent>
        {/* Vertical Timeline */}
        <div className="relative">
          {stages.map((stage, index) => (
            <TimelineNode
              key={stage.id}
              stage={stage}
              isLast={index === stages.length - 1}
              actionsTaken={stage.id === 'tools' ? actionsTaken : undefined}
            />
          ))}
        </div>

        {/* Failed Status Alert */}
        {isFailed && (
          <div className="mt-4 p-4 bg-destructive/10 border border-destructive/20 rounded-lg">
            <div className="flex items-center gap-2 text-destructive">
              <XCircle className="h-4 w-4" />
              <p className="text-sm font-medium">
                Processing failed after maximum retries
              </p>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
