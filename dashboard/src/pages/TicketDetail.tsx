import { useParams, Link } from 'react-router-dom'
import { useTicketWithRefresh, useTicketEventsWithRefresh } from '../hooks/useTickets'
import { StatusBadge } from '../components/StatusBadge'
import { WorkflowProgress } from '../components/WorkflowProgress'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Separator } from '@/components/ui/separator'
import { Skeleton } from '@/components/ui/skeleton'
import {
  ArrowLeft,
  User,
  Mail,
  Calendar,
  Hash,
  MessageSquare,
  Bot,
  Wrench,
  Clock
} from 'lucide-react'

interface ActionTaken {
  tool: string
  args?: Record<string, unknown>
}

function LoadingSkeleton() {
  return (
    <div className="space-y-6">
      <Skeleton className="h-8 w-48" />
      <Skeleton className="h-40 w-full" />
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <Skeleton className="h-64 w-full" />
        </div>
        <Skeleton className="h-64 w-full" />
      </div>
    </div>
  )
}

function formatTimeAgo(dateString: string): string {
  const date = new Date(dateString)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffSecs = Math.floor(diffMs / 1000)
  const diffMins = Math.floor(diffMs / 60000)

  if (diffSecs < 60) return `${diffSecs}s ago`
  if (diffMins < 60) return `${diffMins}m ago`
  return date.toLocaleTimeString()
}

export function TicketDetail() {
  const { id } = useParams<{ id: string }>()
  const { data: ticket, isLoading: ticketLoading, isFetching } = useTicketWithRefresh(id || '', undefined)
  const { data: ticketWithStatus } = useTicketWithRefresh(id || '', ticket?.status)
  const { data: events } = useTicketEventsWithRefresh(id || '', ticket?.status)

  const currentTicket = ticketWithStatus || ticket

  if (ticketLoading) {
    return <LoadingSkeleton />
  }

  if (!currentTicket) {
    return (
      <Card className="border-destructive">
        <CardContent className="pt-6">
          <p className="text-destructive">Ticket not found</p>
        </CardContent>
      </Card>
    )
  }

  const finalResponse = currentTicket.result?.final_response as string | undefined
  const actionsTaken = currentTicket.result?.actions_taken as ActionTaken[] | undefined
  const isProcessing = currentTicket.status === 'pending' || currentTicket.status === 'processing'

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="space-y-1">
          <Link to="/tickets">
            <Button variant="ghost" size="sm" className="gap-2 -ml-2">
              <ArrowLeft className="h-4 w-4" />
              Back to Tickets
            </Button>
          </Link>
          <h1 className="text-2xl font-bold tracking-tight">{currentTicket.subject}</h1>
        </div>
        <StatusBadge status={currentTicket.status} />
      </div>

      {/* Workflow Progress Panel */}
      <WorkflowProgress
        status={currentTicket.status}
        events={events || []}
        actionsTaken={actionsTaken}
        isRefreshing={isFetching && isProcessing}
      />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Main Content */}
        <div className="lg:col-span-2 space-y-6">
          <Card>
            <Tabs defaultValue="message" className="w-full">
              <CardHeader className="pb-0">
                <TabsList className="grid w-full grid-cols-3">
                  <TabsTrigger value="message" className="gap-2">
                    <MessageSquare className="h-4 w-4" />
                    Message
                  </TabsTrigger>
                  <TabsTrigger value="response" className="gap-2" disabled={!finalResponse}>
                    <Bot className="h-4 w-4" />
                    Response
                  </TabsTrigger>
                  <TabsTrigger value="actions" className="gap-2" disabled={!actionsTaken?.length}>
                    <Wrench className="h-4 w-4" />
                    Actions
                  </TabsTrigger>
                </TabsList>
              </CardHeader>

              <CardContent className="pt-6">
                <TabsContent value="message" className="m-0">
                  <div className="rounded-lg bg-muted p-4">
                    <p className="whitespace-pre-wrap text-sm leading-relaxed">
                      {currentTicket.body}
                    </p>
                  </div>
                </TabsContent>

                <TabsContent value="response" className="m-0">
                  {finalResponse ? (
                    <div className="rounded-lg bg-green-50 border border-green-100 p-4">
                      <p className="whitespace-pre-wrap text-sm leading-relaxed">
                        {finalResponse}
                      </p>
                    </div>
                  ) : (
                    <p className="text-muted-foreground text-sm">
                      No response generated yet
                    </p>
                  )}
                </TabsContent>

                <TabsContent value="actions" className="m-0">
                  {actionsTaken && actionsTaken.length > 0 ? (
                    <div className="space-y-3">
                      {actionsTaken.map((action, i) => (
                        <div
                          key={i}
                          className="flex items-start gap-3 rounded-lg border p-3"
                        >
                          <div className="rounded-md bg-primary/10 p-2">
                            <Wrench className="h-4 w-4 text-primary" />
                          </div>
                          <div className="flex-1 min-w-0">
                            <p className="font-medium">
                              {action.tool.replace(/_/g, ' ')}
                            </p>
                            {action.args && (
                              <pre className="mt-1 text-xs text-muted-foreground overflow-x-auto">
                                {JSON.stringify(action.args, null, 2)}
                              </pre>
                            )}
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-muted-foreground text-sm">
                      No actions taken yet
                    </p>
                  )}
                </TabsContent>
              </CardContent>
            </Tabs>
          </Card>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Details */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Details</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center gap-3">
                <User className="h-4 w-4 text-muted-foreground" />
                <div>
                  <p className="text-xs text-muted-foreground">Customer</p>
                  <p className="text-sm font-medium">{currentTicket.customer_id}</p>
                </div>
              </div>

              <Separator />

              <div className="flex items-center gap-3">
                <Mail className="h-4 w-4 text-muted-foreground" />
                <div>
                  <p className="text-xs text-muted-foreground">Channel</p>
                  <p className="text-sm font-medium capitalize">{currentTicket.channel || 'API'}</p>
                </div>
              </div>

              <Separator />

              <div className="flex items-center gap-3">
                <Calendar className="h-4 w-4 text-muted-foreground" />
                <div>
                  <p className="text-xs text-muted-foreground">Created</p>
                  <p className="text-sm font-medium">
                    {new Date(currentTicket.created_at).toLocaleString()}
                  </p>
                </div>
              </div>

              {currentTicket.completed_at && (
                <>
                  <Separator />
                  <div className="flex items-center gap-3">
                    <Calendar className="h-4 w-4 text-muted-foreground" />
                    <div>
                      <p className="text-xs text-muted-foreground">Completed</p>
                      <p className="text-sm font-medium">
                        {new Date(currentTicket.completed_at).toLocaleString()}
                      </p>
                    </div>
                  </div>
                </>
              )}

              <Separator />

              <div className="flex items-center gap-3">
                <Hash className="h-4 w-4 text-muted-foreground" />
                <div>
                  <p className="text-xs text-muted-foreground">Attempts</p>
                  <p className="text-sm font-medium">{currentTicket.attempt_count}</p>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Timeline */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base flex items-center gap-2">
                <Clock className="h-4 w-4" />
                Event Timeline
              </CardTitle>
            </CardHeader>
            <CardContent>
              {!events || events.length === 0 ? (
                <p className="text-muted-foreground text-sm">No events recorded yet</p>
              ) : (
                <div className="space-y-4">
                  {events.map((event, index) => (
                    <div key={event.id} className="flex gap-3">
                      <div className="flex flex-col items-center">
                        <div className={`h-2 w-2 rounded-full ${
                          index === 0 ? 'bg-primary' : 'bg-muted-foreground/30'
                        }`} />
                        {index < events.length - 1 && (
                          <div className="w-px h-full bg-border" />
                        )}
                      </div>
                      <div className="flex-1 pb-4">
                        <p className="text-sm font-medium">
                          {event.step_name || event.event_type}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          {formatTimeAgo(event.created_at)}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
