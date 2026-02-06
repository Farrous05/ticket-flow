import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useApprovals, useDecideApproval } from '../hooks/useApprovals'
import { toast } from 'sonner'
import { StatusBadge } from '../components/StatusBadge'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Textarea } from '@/components/ui/textarea'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import { Separator } from '@/components/ui/separator'
import {
  CheckCircle2,
  XCircle,
  Clock,
  ExternalLink,
  ShieldAlert,
  Loader2,
  DollarSign,
  User
} from 'lucide-react'

function ApprovalSkeleton() {
  return (
    <Card>
      <CardHeader>
        <Skeleton className="h-6 w-48" />
        <Skeleton className="h-4 w-32" />
      </CardHeader>
      <CardContent>
        <Skeleton className="h-24 w-full" />
      </CardContent>
      <CardFooter>
        <Skeleton className="h-10 w-32" />
      </CardFooter>
    </Card>
  )
}

function EmptyState() {
  return (
    <Card className="py-12">
      <CardContent className="flex flex-col items-center justify-center">
        <CheckCircle2 className="h-12 w-12 text-green-500 mb-4" />
        <h3 className="text-lg font-medium">All caught up!</h3>
        <p className="text-muted-foreground mt-1">No pending approvals at this time.</p>
      </CardContent>
    </Card>
  )
}

function formatTimeAgo(dateString: string): string {
  const date = new Date(dateString)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / 60000)
  const diffHours = Math.floor(diffMs / 3600000)

  if (diffMins < 1) return 'Just now'
  if (diffMins < 60) return `${diffMins} minutes ago`
  if (diffHours < 24) return `${diffHours} hours ago`
  return date.toLocaleDateString()
}

export function Approvals() {
  const { data: approvals, isLoading, error } = useApprovals()
  const decideApproval = useDecideApproval()

  const [selectedApproval, setSelectedApproval] = useState<string | null>(null)
  const [decidedBy, setDecidedBy] = useState('')
  const [reason, setReason] = useState('')
  const [isApproving, setIsApproving] = useState(true)

  const handleOpenDialog = (approvalId: string, approve: boolean) => {
    setSelectedApproval(approvalId)
    setIsApproving(approve)
    setReason('')
  }

  const handleDecision = async () => {
    if (!selectedApproval || !decidedBy) return

    try {
      await decideApproval.mutateAsync({
        id: selectedApproval,
        approved: isApproving,
        decidedBy,
        reason: reason || undefined,
      })
      toast.success(isApproving ? 'Action approved' : 'Action rejected', {
        description: `Decision recorded by ${decidedBy}`,
      })
      setSelectedApproval(null)
      setReason('')
    } catch (error) {
      toast.error('Failed to submit decision', {
        description: error instanceof Error ? error.message : 'Please try again',
      })
    }
  }

  const currentApproval = approvals?.find(a => a.id === selectedApproval)

  if (error) {
    return (
      <Card className="border-destructive">
        <CardContent className="pt-6">
          <p className="text-destructive">Error loading approvals. Please try again.</p>
        </CardContent>
      </Card>
    )
  }

  const pendingApprovals = approvals?.filter(a => a.status === 'pending') || []
  const decidedApprovals = approvals?.filter(a => a.status !== 'pending') || []

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Approvals</h1>
        <p className="text-muted-foreground">Review and approve sensitive actions</p>
      </div>

      {/* Approver Name Input */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <User className="h-4 w-4" />
            Your Identity
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-4">
            <div className="flex-1 max-w-sm">
              <Input
                value={decidedBy}
                onChange={(e) => setDecidedBy(e.target.value)}
                placeholder="Enter your name for audit trail"
              />
            </div>
            {decidedBy && (
              <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200">
                <CheckCircle2 className="h-3 w-3 mr-1" />
                Ready to approve
              </Badge>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Pending Approvals */}
      <div className="space-y-4">
        <h2 className="text-lg font-semibold flex items-center gap-2">
          <ShieldAlert className="h-5 w-5 text-amber-500" />
          Pending Approvals
          {pendingApprovals.length > 0 && (
            <Badge variant="secondary">{pendingApprovals.length}</Badge>
          )}
        </h2>

        {isLoading ? (
          <div className="space-y-4">
            <ApprovalSkeleton />
            <ApprovalSkeleton />
          </div>
        ) : pendingApprovals.length === 0 ? (
          <EmptyState />
        ) : (
          <div className="grid gap-4">
            {pendingApprovals.map((approval) => (
              <Card key={approval.id}>
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div>
                      <CardTitle className="flex items-center gap-2">
                        <DollarSign className="h-5 w-5 text-primary" />
                        {approval.action_type.replace(/_/g, ' ').toUpperCase()}
                      </CardTitle>
                      <CardDescription className="mt-1">
                        <Link
                          to={`/tickets/${approval.ticket_id}`}
                          className="inline-flex items-center gap-1 text-primary hover:underline"
                        >
                          View related ticket
                          <ExternalLink className="h-3 w-3" />
                        </Link>
                      </CardDescription>
                    </div>
                    <Badge variant="outline" className="bg-amber-50 text-amber-700 border-amber-200">
                      <Clock className="h-3 w-3 mr-1" />
                      {formatTimeAgo(approval.requested_at)}
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="rounded-lg bg-muted p-4">
                    <h4 className="text-sm font-medium mb-3">Action Details</h4>
                    <dl className="grid grid-cols-2 gap-3">
                      {Object.entries(approval.action_params).map(([key, value]) => (
                        <div key={key}>
                          <dt className="text-xs text-muted-foreground capitalize">{key.replace(/_/g, ' ')}</dt>
                          <dd className="text-sm font-medium">{String(value)}</dd>
                        </div>
                      ))}
                    </dl>
                  </div>
                </CardContent>
                <CardFooter className="flex gap-2">
                  <Button
                    onClick={() => handleOpenDialog(approval.id, true)}
                    disabled={!decidedBy}
                    className="bg-green-600 hover:bg-green-700"
                  >
                    <CheckCircle2 className="mr-2 h-4 w-4" />
                    Approve
                  </Button>
                  <Button
                    variant="destructive"
                    onClick={() => handleOpenDialog(approval.id, false)}
                    disabled={!decidedBy}
                  >
                    <XCircle className="mr-2 h-4 w-4" />
                    Reject
                  </Button>
                </CardFooter>
              </Card>
            ))}
          </div>
        )}
      </div>

      {/* Decided Approvals */}
      {decidedApprovals.length > 0 && (
        <div className="space-y-4">
          <Separator />
          <h2 className="text-lg font-semibold text-muted-foreground">Recent Decisions</h2>
          <div className="grid gap-4">
            {decidedApprovals.slice(0, 5).map((approval) => (
              <Card key={approval.id} className="opacity-75">
                <CardHeader className="pb-3">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-base">
                      {approval.action_type.replace(/_/g, ' ').toUpperCase()}
                    </CardTitle>
                    <StatusBadge status={approval.status} />
                  </div>
                </CardHeader>
                <CardContent className="text-sm text-muted-foreground">
                  <p>
                    {approval.status === 'approved' ? 'Approved' : 'Rejected'} by{' '}
                    <span className="font-medium text-foreground">{approval.decided_by}</span>
                    {approval.decided_at && (
                      <> on {new Date(approval.decided_at).toLocaleString()}</>
                    )}
                  </p>
                  {approval.decision_reason && (
                    <p className="mt-1 italic">"{approval.decision_reason}"</p>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}

      {/* Decision Dialog */}
      <Dialog open={!!selectedApproval} onOpenChange={(open) => !open && setSelectedApproval(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              {isApproving ? 'Approve Action' : 'Reject Action'}
            </DialogTitle>
            <DialogDescription>
              You are about to {isApproving ? 'approve' : 'reject'} the{' '}
              <span className="font-medium">
                {currentApproval?.action_type.replace(/_/g, ' ')}
              </span>{' '}
              action. This decision will be recorded in the audit log.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="reason">Reason (optional)</Label>
              <Textarea
                id="reason"
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                placeholder="Add a note explaining your decision..."
                rows={3}
              />
            </div>
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={() => setSelectedApproval(null)}>
              Cancel
            </Button>
            <Button
              onClick={handleDecision}
              disabled={decideApproval.isPending}
              className={isApproving ? 'bg-green-600 hover:bg-green-700' : ''}
              variant={isApproving ? 'default' : 'destructive'}
            >
              {decideApproval.isPending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Processing...
                </>
              ) : (
                <>
                  {isApproving ? (
                    <CheckCircle2 className="mr-2 h-4 w-4" />
                  ) : (
                    <XCircle className="mr-2 h-4 w-4" />
                  )}
                  {isApproving ? 'Confirm Approval' : 'Confirm Rejection'}
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
