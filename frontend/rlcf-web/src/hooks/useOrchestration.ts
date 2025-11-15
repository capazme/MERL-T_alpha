/**
 * TanStack Query hooks for Orchestration API
 *
 * Provides hooks for query execution monitoring, execution trace viewing,
 * and pipeline metrics visualization.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../lib/api';

// --- Query Keys ---
const orchestrationKeys = {
  all: ['orchestration'] as const,
  queries: () => [...orchestrationKeys.all, 'queries'] as const,
  query: (traceId: string) => [...orchestrationKeys.queries(), traceId] as const,
  queryStatus: (traceId: string) => [...orchestrationKeys.query(traceId), 'status'] as const,
  queryHistory: (userId: string, params?: any) => [...orchestrationKeys.queries(), 'history', userId, params] as const,
  feedbackStats: () => [...orchestrationKeys.all, 'feedback-stats'] as const,
};

// --- Hooks ---

/**
 * Execute a query through the orchestration pipeline
 */
export function useExecuteQuery() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (request: { query: string; context?: any; options?: any }) =>
      apiClient.orchestration.executeQuery(request),
    onSuccess: () => {
      // Invalidate queries list after successful execution
      queryClient.invalidateQueries({ queryKey: orchestrationKeys.queries() });
    },
  });
}

/**
 * Get query execution status by trace ID
 */
export function useQueryStatus(traceId: string | null, options?: { refetchInterval?: number }) {
  return useQuery({
    queryKey: orchestrationKeys.queryStatus(traceId || ''),
    queryFn: () => apiClient.orchestration.getQueryStatus(traceId!),
    enabled: !!traceId,
    refetchInterval: options?.refetchInterval || false,
    staleTime: 5000, // Consider stale after 5 seconds
  });
}

/**
 * Get complete query details including execution trace
 */
export function useQueryDetails(traceId: string | null) {
  return useQuery({
    queryKey: orchestrationKeys.query(traceId || ''),
    queryFn: () => apiClient.orchestration.retrieveQuery(traceId!),
    enabled: !!traceId,
    staleTime: 60000, // Cache for 1 minute
  });
}

/**
 * Get query history for a user
 */
export function useQueryHistory(
  userId: string | null,
  params?: { limit?: number; offset?: number; since?: string }
) {
  return useQuery({
    queryKey: orchestrationKeys.queryHistory(userId || '', params),
    queryFn: () => apiClient.orchestration.getQueryHistory(userId!, params),
    enabled: !!userId,
    staleTime: 30000, // Cache for 30 seconds
  });
}

/**
 * Submit user feedback for a query
 */
export function useSubmitUserFeedback() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (feedback: { trace_id: string; rating: number; feedback_text?: string | null; categories?: any }) =>
      apiClient.orchestration.submitUserFeedback(feedback),
    onSuccess: (_, variables) => {
      // Invalidate query details to refresh feedback list
      queryClient.invalidateQueries({ queryKey: orchestrationKeys.query(variables.trace_id) });
      queryClient.invalidateQueries({ queryKey: orchestrationKeys.feedbackStats() });
    },
  });
}

/**
 * Submit RLCF expert feedback
 */
export function useSubmitRlcfFeedback() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (feedback: { trace_id: string; expert_id: string; authority_score?: number; corrections: any }) =>
      apiClient.orchestration.submitRlcfFeedback(feedback),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: orchestrationKeys.query(variables.trace_id) });
      queryClient.invalidateQueries({ queryKey: orchestrationKeys.feedbackStats() });
    },
  });
}

/**
 * Submit NER correction
 */
export function useSubmitNerCorrection() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (correction: { trace_id: string; correction_type: string; correction_data: any }) =>
      apiClient.orchestration.submitNerCorrection(correction),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: orchestrationKeys.query(variables.trace_id) });
      queryClient.invalidateQueries({ queryKey: orchestrationKeys.feedbackStats() });
    },
  });
}

/**
 * Get feedback statistics
 */
export function useFeedbackStats() {
  return useQuery({
    queryKey: orchestrationKeys.feedbackStats(),
    queryFn: () => apiClient.orchestration.getFeedbackStats(),
    staleTime: 60000, // Cache for 1 minute
    refetchInterval: 60000, // Refresh every minute
  });
}

/**
 * Poll query status until completion
 * Returns query status with automatic polling every 2 seconds if status is pending/processing
 */
export function usePollQueryStatus(traceId: string | null) {
  const { data: status } = useQueryStatus(traceId, {
    refetchInterval: (query) => {
      const currentStatus = query.state.data?.status;
      // Poll every 2 seconds if status is pending or processing
      if (currentStatus === 'pending' || currentStatus === 'processing') {
        return 2000;
      }
      // Stop polling if completed, failed, or timeout
      return false;
    },
  });

  return status;
}
