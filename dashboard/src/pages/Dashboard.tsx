import { Link } from 'react-router-dom'
import { useDashboardStats } from '../hooks/useTickets'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Ticket,
  Clock,
  Loader2,
  ShieldAlert,
  CheckCircle,
  XCircle,
  Plus,
  ArrowRight,
  AlertTriangle
} from 'lucide-react'

interface StatCardProps {
  title: string
  value: number
  icon: React.ComponentType<{ className?: string }>
  iconColor: string
  bgColor: string
}

function StatCard({ title, value, icon: Icon, iconColor, bgColor }: StatCardProps) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">{title}</CardTitle>
        <div className={`rounded-md p-2 ${bgColor}`}>
          <Icon className={`h-4 w-4 ${iconColor}`} />
        </div>
      </CardHeader>
      <CardContent>
        <div className="text-3xl font-bold">{value}</div>
      </CardContent>
    </Card>
  )
}

function StatCardSkeleton() {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <Skeleton className="h-4 w-24" />
        <Skeleton className="h-8 w-8 rounded-md" />
      </CardHeader>
      <CardContent>
        <Skeleton className="h-8 w-16" />
      </CardContent>
    </Card>
  )
}

export function Dashboard() {
  const { data: stats, isLoading, error } = useDashboardStats()

  if (error) {
    return (
      <Alert variant="destructive">
        <AlertTriangle className="h-4 w-4" />
        <AlertTitle>Error</AlertTitle>
        <AlertDescription>Failed to load dashboard stats. Please try again.</AlertDescription>
      </Alert>
    )
  }

  const statCards = [
    { title: 'Total Tickets', value: stats?.total_tickets || 0, icon: Ticket, iconColor: 'text-slate-600', bgColor: 'bg-slate-100' },
    { title: 'Pending', value: stats?.pending_tickets || 0, icon: Clock, iconColor: 'text-amber-600', bgColor: 'bg-amber-100' },
    { title: 'Processing', value: stats?.processing_tickets || 0, icon: Loader2, iconColor: 'text-blue-600', bgColor: 'bg-blue-100' },
    { title: 'Awaiting Approval', value: stats?.awaiting_approval_tickets || 0, icon: ShieldAlert, iconColor: 'text-purple-600', bgColor: 'bg-purple-100' },
    { title: 'Completed', value: stats?.completed_tickets || 0, icon: CheckCircle, iconColor: 'text-green-600', bgColor: 'bg-green-100' },
    { title: 'Failed', value: stats?.failed_tickets || 0, icon: XCircle, iconColor: 'text-red-600', bgColor: 'bg-red-100' },
  ]

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Dashboard</h1>
          <p className="text-muted-foreground">Overview of your ticket processing system</p>
        </div>
        <Link to="/tickets/new">
          <Button>
            <Plus className="mr-2 h-4 w-4" />
            New Ticket
          </Button>
        </Link>
      </div>

      {/* Pending Approvals Alert */}
      {stats && stats.pending_approvals > 0 && (
        <Alert className="border-purple-200 bg-purple-50">
          <ShieldAlert className="h-4 w-4 text-purple-600" />
          <AlertTitle className="text-purple-800">Action Required</AlertTitle>
          <AlertDescription className="text-purple-700">
            You have {stats.pending_approvals} pending approval{stats.pending_approvals > 1 ? 's' : ''} that need your attention.
            <Link to="/approvals" className="ml-2 font-medium underline hover:no-underline">
              Review now
            </Link>
          </AlertDescription>
        </Alert>
      )}

      {/* Stats Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
        {isLoading
          ? Array(6).fill(0).map((_, i) => <StatCardSkeleton key={i} />)
          : statCards.map((stat) => (
              <StatCard key={stat.title} {...stat} />
            ))
        }
      </div>

      {/* Quick Actions */}
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Quick Actions</CardTitle>
            <CardDescription>Common tasks at your fingertips</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-2">
            <Link to="/tickets/new">
              <Button variant="outline" className="w-full justify-between">
                Create New Ticket
                <ArrowRight className="h-4 w-4" />
              </Button>
            </Link>
            <Link to="/tickets">
              <Button variant="outline" className="w-full justify-between">
                View All Tickets
                <ArrowRight className="h-4 w-4" />
              </Button>
            </Link>
            <Link to="/approvals">
              <Button variant="outline" className="w-full justify-between">
                Review Approvals
                <ArrowRight className="h-4 w-4" />
              </Button>
            </Link>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>System Status</CardTitle>
            <CardDescription>Current system health</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">API Status</span>
                <span className="flex items-center gap-2 text-sm font-medium text-green-600">
                  <span className="h-2 w-2 rounded-full bg-green-500" />
                  Operational
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Worker Status</span>
                <span className="flex items-center gap-2 text-sm font-medium text-green-600">
                  <span className="h-2 w-2 rounded-full bg-green-500" />
                  Running
                </span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm text-muted-foreground">Queue</span>
                <span className="text-sm font-medium">
                  {stats?.pending_tickets || 0} pending
                </span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
