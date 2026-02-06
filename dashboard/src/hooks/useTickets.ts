import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api, CreateTicketRequest } from '../api/client'

export function useTickets(page = 1, pageSize = 20, status?: string) {
  return useQuery({
    queryKey: ['tickets', page, pageSize, status],
    queryFn: () => api.listTickets(page, pageSize, status),
  })
}

export function useTicket(id: string) {
  return useQuery({
    queryKey: ['ticket', id],
    queryFn: () => api.getTicket(id),
    enabled: !!id,
  })
}

export function useTicketEvents(id: string) {
  return useQuery({
    queryKey: ['ticket-events', id],
    queryFn: () => api.getTicketEvents(id),
    enabled: !!id,
  })
}

export function useDashboardStats() {
  return useQuery({
    queryKey: ['dashboard-stats'],
    queryFn: () => api.getStats(),
    refetchInterval: 30000, // Refresh every 30 seconds
  })
}

export function useCreateTicket() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (data: CreateTicketRequest) => api.createTicket(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tickets'] })
      queryClient.invalidateQueries({ queryKey: ['dashboard-stats'] })
    },
  })
}

// Auto-refreshing version for watching ticket processing
export function useTicketWithRefresh(id: string, status?: string) {
  const shouldRefresh = status === 'pending' || status === 'processing'
  return useQuery({
    queryKey: ['ticket', id],
    queryFn: () => api.getTicket(id),
    enabled: !!id,
    refetchInterval: shouldRefresh ? 3000 : false, // Refresh every 3 seconds while processing
  })
}

export function useTicketEventsWithRefresh(id: string, status?: string) {
  const shouldRefresh = status === 'pending' || status === 'processing'
  return useQuery({
    queryKey: ['ticket-events', id],
    queryFn: () => api.getTicketEvents(id),
    enabled: !!id,
    refetchInterval: shouldRefresh ? 3000 : false,
  })
}
