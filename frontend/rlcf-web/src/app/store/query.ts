/**
 * Query Store
 *
 * Zustand store for managing query submission state and context.
 * Tracks current query, options, context, and recent queries.
 */

import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import type {
  QueryContext,
  QueryOptions,
  QueryHistoryItem,
} from '@/types/orchestration';

// ============================================================================
// STATE INTERFACE
// ============================================================================

interface QueryState {
  /** Current query text */
  currentQuery: string;
  /** Current trace ID (if query is executing/completed) */
  currentTraceId: string | null;
  /** Query context options */
  queryContext: QueryContext;
  /** Query execution options */
  queryOptions: QueryOptions;
  /** Recent queries (cached from history API) */
  recentQueries: QueryHistoryItem[];
  /** Loading state for query submission */
  isSubmitting: boolean;
  /** Error message (if any) */
  error: string | null;
}

// ============================================================================
// ACTIONS INTERFACE
// ============================================================================

interface QueryActions {
  /** Set the current query text */
  setCurrentQuery: (query: string) => void;

  /** Set the current trace ID */
  setCurrentTraceId: (traceId: string | null) => void;

  /** Update query context (partial update) */
  updateContext: (context: Partial<QueryContext>) => void;

  /** Reset query context to defaults */
  resetContext: () => void;

  /** Update query options (partial update) */
  updateOptions: (options: Partial<QueryOptions>) => void;

  /** Reset query options to defaults */
  resetOptions: () => void;

  /** Add a query to recent queries */
  addToRecent: (query: QueryHistoryItem) => void;

  /** Set recent queries (from API) */
  setRecentQueries: (queries: QueryHistoryItem[]) => void;

  /** Set submitting state */
  setSubmitting: (isSubmitting: boolean) => void;

  /** Set error message */
  setError: (error: string | null) => void;

  /** Clear error */
  clearError: () => void;

  /** Reset entire store to defaults */
  reset: () => void;

  /** Pre-fill form with a previous query */
  loadQuery: (query: QueryHistoryItem) => void;
}

// ============================================================================
// STORE TYPE
// ============================================================================

type QueryStore = QueryState & QueryActions;

// ============================================================================
// DEFAULT VALUES
// ============================================================================

const DEFAULT_CONTEXT: QueryContext = {
  temporal_reference: 'latest',
  jurisdiction: 'nazionale',
  user_role: 'cittadino',
  previous_queries: null,
};

const DEFAULT_OPTIONS: QueryOptions = {
  max_iterations: 3,
  return_trace: true,
  stream_response: false,
  timeout_ms: 30000,
};

const INITIAL_STATE: QueryState = {
  currentQuery: '',
  currentTraceId: null,
  queryContext: DEFAULT_CONTEXT,
  queryOptions: DEFAULT_OPTIONS,
  recentQueries: [],
  isSubmitting: false,
  error: null,
};

// ============================================================================
// STORE CREATION
// ============================================================================

export const useQueryStore = create<QueryStore>()(
  persist(
    (set, get) => ({
      // Initial state
      ...INITIAL_STATE,

      // Actions
      setCurrentQuery: (query) => {
        set({ currentQuery: query, error: null });
      },

      setCurrentTraceId: (traceId) => {
        set({ currentTraceId: traceId });
      },

      updateContext: (context) => {
        set((state) => ({
          queryContext: {
            ...state.queryContext,
            ...context,
          },
        }));
      },

      resetContext: () => {
        set({ queryContext: DEFAULT_CONTEXT });
      },

      updateOptions: (options) => {
        set((state) => ({
          queryOptions: {
            ...state.queryOptions,
            ...options,
          },
        }));
      },

      resetOptions: () => {
        set({ queryOptions: DEFAULT_OPTIONS });
      },

      addToRecent: (query) => {
        set((state) => {
          // Prevent duplicates
          const existing = state.recentQueries.find((q) => q.trace_id === query.trace_id);
          if (existing) {
            return state;
          }

          // Keep max 20 recent queries
          const newRecent = [query, ...state.recentQueries].slice(0, 20);
          return { recentQueries: newRecent };
        });
      },

      setRecentQueries: (queries) => {
        set({ recentQueries: queries.slice(0, 20) });
      },

      setSubmitting: (isSubmitting) => {
        set({ isSubmitting });
      },

      setError: (error) => {
        set({ error });
      },

      clearError: () => {
        set({ error: null });
      },

      reset: () => {
        set(INITIAL_STATE);
      },

      loadQuery: (query) => {
        set({
          currentQuery: query.query,
          currentTraceId: query.trace_id,
          error: null,
        });
      },
    }),
    {
      name: 'merl-t-query-store',
      storage: createJSONStorage(() => localStorage),
      // Persist only these fields (exclude isSubmitting and error)
      partialize: (state) => ({
        currentQuery: state.currentQuery,
        queryContext: state.queryContext,
        queryOptions: state.queryOptions,
        recentQueries: state.recentQueries,
      }),
    }
  )
);

// ============================================================================
// SELECTOR HOOKS (for optimized re-renders)
// ============================================================================

/** Get current query text */
export const useCurrentQuery = () => useQueryStore((state) => state.currentQuery);

/** Get current trace ID */
export const useCurrentTraceId = () => useQueryStore((state) => state.currentTraceId);

/** Get query context */
export const useQueryContext = () => useQueryStore((state) => state.queryContext);

/** Get query options */
export const useQueryOptions = () => useQueryStore((state) => state.queryOptions);

/** Get recent queries */
export const useRecentQueries = () => useQueryStore((state) => state.recentQueries);

/** Get submitting state */
export const useIsSubmitting = () => useQueryStore((state) => state.isSubmitting);

/** Get error state */
export const useQueryError = () => useQueryStore((state) => state.error);
