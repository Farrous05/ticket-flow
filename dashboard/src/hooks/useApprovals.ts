import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'

export function useApprovals() {
  return useQuery({
    queryKey: ['approvals'],
    queryFn: () => api.listApprovals(),
    refetchInterval: 10000, // Refresh every 10 seconds
  })
}

export function useApproval(id: string) {
  return useQuery({
    queryKey: ['approval', id],
    queryFn: () => api.getApproval(id),
    enabled: !!id,
  })
}

export function useDecideApproval() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({
      id,
      approved,
      decidedBy,
      reason,
    }: {
      id: string
      approved: boolean
      decidedBy: string
      reason?: string
    }) => api.decideApproval(id, approved, decidedBy, reason),
    onSuccess: () => {
      // Invalidate related queries
      queryClient.invalidateQueries({ queryKey: ['approvals'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard-stats'] })
    },
  })
}
