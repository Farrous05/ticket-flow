import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useTickets } from '../hooks/useTickets'
import { StatusBadge } from '../components/StatusBadge'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Input } from '@/components/ui/input'
import { Skeleton } from '@/components/ui/skeleton'
import { Plus, Search, ChevronLeft, ChevronRight, Inbox, ExternalLink } from 'lucide-react'

function TableSkeleton() {
  return (
    <>
      {Array(5).fill(0).map((_, i) => (
        <TableRow key={i}>
          <TableCell><Skeleton className="h-4 w-48" /></TableCell>
          <TableCell><Skeleton className="h-4 w-32" /></TableCell>
          <TableCell><Skeleton className="h-6 w-20" /></TableCell>
          <TableCell><Skeleton className="h-4 w-16" /></TableCell>
          <TableCell><Skeleton className="h-4 w-28" /></TableCell>
        </TableRow>
      ))}
    </>
  )
}

function EmptyState() {
  return (
    <TableRow>
      <TableCell colSpan={5}>
        <div className="flex flex-col items-center justify-center py-12">
          <Inbox className="h-12 w-12 text-muted-foreground mb-4" />
          <h3 className="text-lg font-medium">No tickets found</h3>
          <p className="text-muted-foreground mt-1 mb-4">
            Create your first ticket to get started
          </p>
          <Link to="/tickets/new">
            <Button>
              <Plus className="mr-2 h-4 w-4" />
              New Ticket
            </Button>
          </Link>
        </div>
      </TableCell>
    </TableRow>
  )
}

function formatTimeAgo(dateString: string): string {
  const date = new Date(dateString)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMs / 3600000)
  const diffDays = Math.floor(diffMs / 86400000)

  if (diffMins < 1) return 'Just now'
  if (diffMins < 60) return `${diffMins}m ago`
  if (diffHours < 24) return `${diffHours}h ago`
  if (diffDays < 7) return `${diffDays}d ago`
  return date.toLocaleDateString()
}

export function Tickets() {
  const [page, setPage] = useState(1)
  const [statusFilter, setStatusFilter] = useState<string | undefined>()
  const { data, isLoading, error } = useTickets(page, 20, statusFilter)

  if (error) {
    return (
      <Card className="border-destructive">
        <CardContent className="pt-6">
          <p className="text-destructive">Error loading tickets. Please try again.</p>
        </CardContent>
      </Card>
    )
  }

  const totalPages = data ? Math.ceil(data.total / 20) : 1

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Tickets</h1>
          <p className="text-muted-foreground">Manage and track support tickets</p>
        </div>
        <Link to="/tickets/new">
          <Button>
            <Plus className="mr-2 h-4 w-4" />
            New Ticket
          </Button>
        </Link>
      </div>

      {/* Filters */}
      <Card>
        <CardHeader className="pb-4">
          <CardTitle className="text-base">Filters</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex gap-4">
            <div className="relative flex-1 max-w-sm">
              <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="Search tickets..."
                className="pl-9"
                disabled
              />
            </div>
            <Select
              value={statusFilter || 'all'}
              onValueChange={(value) => {
                setStatusFilter(value === 'all' ? undefined : value)
                setPage(1)
              }}
            >
              <SelectTrigger className="w-[180px]">
                <SelectValue placeholder="Status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Status</SelectItem>
                <SelectItem value="pending">Pending</SelectItem>
                <SelectItem value="processing">Processing</SelectItem>
                <SelectItem value="awaiting_approval">Awaiting Approval</SelectItem>
                <SelectItem value="completed">Completed</SelectItem>
                <SelectItem value="failed_permanent">Failed</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Tickets Table */}
      <Card>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Subject</TableHead>
              <TableHead>Customer</TableHead>
              <TableHead>Status</TableHead>
              <TableHead>Channel</TableHead>
              <TableHead>Created</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {isLoading ? (
              <TableSkeleton />
            ) : data?.tickets.length === 0 ? (
              <EmptyState />
            ) : (
              data?.tickets.map((ticket) => (
                <TableRow key={ticket.id} className="cursor-pointer hover:bg-muted/50">
                  <TableCell>
                    <Link
                      to={`/tickets/${ticket.id}`}
                      className="flex items-center gap-2 font-medium text-primary hover:underline"
                    >
                      {ticket.subject.length > 50
                        ? `${ticket.subject.substring(0, 50)}...`
                        : ticket.subject}
                      <ExternalLink className="h-3 w-3 opacity-50" />
                    </Link>
                  </TableCell>
                  <TableCell className="text-muted-foreground">{ticket.customer_id}</TableCell>
                  <TableCell>
                    <StatusBadge status={ticket.status} />
                  </TableCell>
                  <TableCell className="text-muted-foreground capitalize">{ticket.channel || 'api'}</TableCell>
                  <TableCell className="text-muted-foreground">{formatTimeAgo(ticket.created_at)}</TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>

        {/* Pagination */}
        {data && data.total > 0 && (
          <div className="flex items-center justify-between border-t px-4 py-3">
            <p className="text-sm text-muted-foreground">
              Showing {((page - 1) * 20) + 1} to {Math.min(page * 20, data.total)} of {data.total} tickets
            </p>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
              >
                <ChevronLeft className="h-4 w-4" />
                Previous
              </Button>
              <div className="flex items-center gap-1 px-2">
                <span className="text-sm font-medium">{page}</span>
                <span className="text-sm text-muted-foreground">of</span>
                <span className="text-sm font-medium">{totalPages}</span>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={() => setPage((p) => p + 1)}
                disabled={page >= totalPages}
              >
                Next
                <ChevronRight className="h-4 w-4" />
              </Button>
            </div>
          </div>
        )}
      </Card>
    </div>
  )
}
