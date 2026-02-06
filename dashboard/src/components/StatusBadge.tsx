import { Badge } from '@/components/ui/badge'
import {
  Clock,
  Loader2,
  ShieldAlert,
  CheckCircle,
  XCircle,
  ThumbsUp,
  ThumbsDown
} from 'lucide-react'
import { cn } from '@/lib/utils'

type Status = 'pending' | 'processing' | 'awaiting_approval' | 'completed' | 'failed_permanent' | 'approved' | 'rejected'

interface StatusConfig {
  label: string
  icon: React.ComponentType<{ className?: string }>
  className: string
  iconClassName?: string
}

const statusConfig: Record<Status, StatusConfig> = {
  pending: {
    label: 'Pending',
    icon: Clock,
    className: 'bg-amber-100 text-amber-700 hover:bg-amber-100 border-amber-200',
  },
  processing: {
    label: 'Processing',
    icon: Loader2,
    className: 'bg-blue-100 text-blue-700 hover:bg-blue-100 border-blue-200',
    iconClassName: 'animate-spin',
  },
  awaiting_approval: {
    label: 'Needs Approval',
    icon: ShieldAlert,
    className: 'bg-purple-100 text-purple-700 hover:bg-purple-100 border-purple-200',
  },
  completed: {
    label: 'Completed',
    icon: CheckCircle,
    className: 'bg-green-100 text-green-700 hover:bg-green-100 border-green-200',
  },
  failed_permanent: {
    label: 'Failed',
    icon: XCircle,
    className: 'bg-red-100 text-red-700 hover:bg-red-100 border-red-200',
  },
  approved: {
    label: 'Approved',
    icon: ThumbsUp,
    className: 'bg-green-100 text-green-700 hover:bg-green-100 border-green-200',
  },
  rejected: {
    label: 'Rejected',
    icon: ThumbsDown,
    className: 'bg-red-100 text-red-700 hover:bg-red-100 border-red-200',
  },
}

export function StatusBadge({ status }: { status: Status }) {
  const config = statusConfig[status] || {
    label: status,
    icon: Clock,
    className: 'bg-gray-100 text-gray-700 hover:bg-gray-100 border-gray-200',
  }

  const Icon = config.icon

  return (
    <Badge
      variant="outline"
      className={cn("gap-1 font-medium", config.className)}
    >
      <Icon className={cn("h-3 w-3", config.iconClassName)} />
      {config.label}
    </Badge>
  )
}
