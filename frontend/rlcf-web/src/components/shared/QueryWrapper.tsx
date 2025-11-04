import { type ReactNode } from 'react';
import type { UseQueryResult } from '@tanstack/react-query';
import { LoadingFallback, EmptyStateFallback, SimpleErrorFallback } from './ErrorBoundary';
import { AlertTriangle } from 'lucide-react';

interface QueryWrapperProps<T> {
  query: UseQueryResult<T>;
  children: (data: T) => ReactNode;
  loadingMessage?: string;
  emptyMessage?: string;
  emptyAction?: ReactNode;
  errorRetryable?: boolean;
  showErrorDetails?: boolean;
  minHeight?: string;
}

export function QueryWrapper<T>({
  query,
  children,
  loadingMessage = 'Loading...',
  emptyMessage = 'No data available',
  emptyAction,
  errorRetryable = true,
  showErrorDetails = false,
  minHeight = '200px',
}: QueryWrapperProps<T>) {
  const { data, isLoading, error, refetch, isFetching } = query;

  // Loading state
  if (isLoading) {
    return (
      <div style={{ minHeight }} className="flex items-center justify-center">
        <LoadingFallback message={loadingMessage} />
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div style={{ minHeight }} className="flex items-center justify-center">
        <div className="text-center p-6 max-w-md">
          <AlertTriangle className="h-12 w-12 text-red-400 mx-auto mb-4" />
          <h3 className="text-lg font-semibold text-white mb-2">Failed to load data</h3>
          <p className="text-slate-400 text-sm mb-4">
            {error instanceof Error ? error.message : 'An unexpected error occurred'}
          </p>
          
          {showErrorDetails && error instanceof Error && (
            <details className="mb-4 text-left">
              <summary className="cursor-pointer text-xs text-slate-500 hover:text-slate-400">
                Technical Details
              </summary>
              <pre className="mt-2 p-2 bg-slate-800 rounded text-xs text-red-400 overflow-auto max-h-32">
                {error.stack}
              </pre>
            </details>
          )}
          
          {errorRetryable && (
            <button
              onClick={() => refetch()}
              className="px-4 py-2 bg-violet-600 hover:bg-violet-700 text-white rounded-md text-sm transition-colors"
              disabled={isFetching}
            >
              {isFetching ? 'Retrying...' : 'Try Again'}
            </button>
          )}
        </div>
      </div>
    );
  }

  // Empty state
  if (!data || (Array.isArray(data) && data.length === 0)) {
    return (
      <div style={{ minHeight }} className="flex items-center justify-center">
        <EmptyStateFallback message={emptyMessage} action={emptyAction} />
      </div>
    );
  }

  // Success state
  return (
    <div className="relative">
      {/* Show loading overlay during refetch */}
      {isFetching && !isLoading && (
        <div className="absolute inset-0 bg-slate-900/50 backdrop-blur-sm flex items-center justify-center z-10 rounded-lg">
          <div className="bg-slate-800 px-4 py-2 rounded-lg border border-slate-700 flex items-center gap-2">
            <div className="animate-spin h-4 w-4 border-2 border-violet-500 border-t-transparent rounded-full"></div>
            <span className="text-sm text-slate-300">Updating...</span>
          </div>
        </div>
      )}
      {children(data)}
    </div>
  );
}

// Specialized wrapper for arrays with count
export function QueryListWrapper<T extends any[]>({
  query,
  children,
  loadingMessage = 'Loading items...',
  emptyMessage = 'No items found',
  emptyAction,
  itemName = 'items',
  ...props
}: Omit<QueryWrapperProps<T>, 'children'> & {
  children: (data: T, count: number) => ReactNode;
  itemName?: string;
  emptyMessage?: string;
}) {
  return (
    <QueryWrapper
      query={query}
      loadingMessage={loadingMessage}
      emptyMessage={`No ${itemName} ${emptyMessage.toLowerCase()}`}
      emptyAction={emptyAction}
      {...props}
    >
      {(data) => children(data, data.length)}
    </QueryWrapper>
  );
}

// Multiple queries wrapper
interface MultiQueryWrapperProps {
  queries: UseQueryResult<any>[];
  children: (data: any[]) => ReactNode;
  loadingMessage?: string;
  errorMessage?: string;
}

export function MultiQueryWrapper({
  queries,
  children,
  loadingMessage = 'Loading data...',
  errorMessage = 'Failed to load some data',
}: MultiQueryWrapperProps) {
  const isLoading = queries.some(q => q.isLoading);
  const hasError = queries.some(q => q.error);
  const isFetching = queries.some(q => q.isFetching);

  if (isLoading) {
    return <LoadingFallback message={loadingMessage} />;
  }

  if (hasError) {
    const errors = queries.filter(q => q.error).map(q => q.error);
    return (
      <SimpleErrorFallback
        error={new Error(errors.map(e => e?.message || 'Unknown error').join(', '))}
        resetError={() => queries.forEach(q => q.refetch())}
      />
    );
  }

  return (
    <div className="relative">
      {isFetching && (
        <div className="absolute top-0 right-0 m-4 z-10">
          <div className="bg-slate-800 px-3 py-1 rounded-full border border-slate-700 flex items-center gap-2">
            <div className="animate-spin h-3 w-3 border border-violet-500 border-t-transparent rounded-full"></div>
            <span className="text-xs text-slate-400">Syncing...</span>
          </div>
        </div>
      )}
      {children(queries.map(q => q.data))}
    </div>
  );
}