/**
 * Query Monitor Dashboard
 *
 * Real-time monitoring of query execution through the orchestration pipeline.
 * Shows query list, status, execution timeline, and drill-down to detailed traces.
 */

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@components/ui/Card';
import { Button } from '@components/ui/Button';
import { Badge } from '@components/ui/Badge';
import { useQueryHistory, usePollQueryStatus } from '@hooks/useOrchestration';
import { RefreshCw, Eye, Clock, CheckCircle, XCircle, Loader } from 'lucide-react';
import { ExecutionTraceViewer } from './ExecutionTraceViewer';

type QueryStatus = 'pending' | 'processing' | 'completed' | 'failed' | 'timeout';

interface QueryListItem {
  trace_id: string;
  query_text: string;
  timestamp: string;
  status?: QueryStatus;
  confidence?: number;
}

export function QueryMonitorDashboard() {
  const [selectedTraceId, setSelectedTraceId] = useState<string | null>(null);
  const [userId] = useState('1'); // TODO: Get from auth context

  // Fetch query history (last 50 queries)
  const { data: historyData, isLoading, refetch } = useQueryHistory(userId, { limit: 50, offset: 0 });

  const queries: QueryListItem[] = historyData?.queries || [];

  const getStatusBadge = (status?: QueryStatus) => {
    if (!status) return <Badge variant="default">Unknown</Badge>;

    const variants: Record<QueryStatus, { icon: React.ReactNode; variant: 'default' | 'outline' | 'secondary'; label: string }> = {
      pending: { icon: <Clock className="w-3 h-3 mr-1" />, variant: 'outline', label: 'Pending' },
      processing: { icon: <Loader className="w-3 h-3 mr-1 animate-spin" />, variant: 'default', label: 'Processing' },
      completed: { icon: <CheckCircle className="w-3 h-3 mr-1" />, variant: 'secondary', label: 'Completed' },
      failed: { icon: <XCircle className="w-3 h-3 mr-1" />, variant: 'outline', label: 'Failed' },
      timeout: { icon: <XCircle className="w-3 h-3 mr-1" />, variant: 'outline', label: 'Timeout' },
    };

    const config = variants[status];
    return (
      <Badge variant={config.variant} className="flex items-center">
        {config.icon}
        {config.label}
      </Badge>
    );
  };

  // If a query is selected, show detailed trace viewer
  if (selectedTraceId) {
    return (
      <div className="space-y-4">
        <Button onClick={() => setSelectedTraceId(null)} variant="outline">
          ← Back to Query List
        </Button>
        <ExecutionTraceViewer traceId={selectedTraceId} />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Query Monitor</h1>
          <p className="text-gray-400 mt-1">Real-time orchestration pipeline monitoring</p>
        </div>
        <Button onClick={() => refetch()} variant="outline" className="flex items-center gap-2">
          <RefreshCw className="w-4 h-4" />
          Refresh
        </Button>
      </div>

      {/* Query List */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Queries ({queries.length})</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading ? (
            <div className="flex items-center justify-center py-8 text-gray-400">
              <Loader className="w-6 h-6 animate-spin mr-2" />
              Loading queries...
            </div>
          ) : queries.length === 0 ? (
            <div className="text-center py-8 text-gray-400">
              No queries found. Execute a query to see it here.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr className="border-b border-gray-700">
                    <th className="text-left py-3 px-4 text-gray-400 font-medium">Trace ID</th>
                    <th className="text-left py-3 px-4 text-gray-400 font-medium">Query</th>
                    <th className="text-left py-3 px-4 text-gray-400 font-medium">Status</th>
                    <th className="text-left py-3 px-4 text-gray-400 font-medium">Confidence</th>
                    <th className="text-left py-3 px-4 text-gray-400 font-medium">Timestamp</th>
                    <th className="text-left py-3 px-4 text-gray-400 font-medium">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {queries.map((query) => (
                    <QueryRow
                      key={query.trace_id}
                      query={query}
                      onViewDetails={() => setSelectedTraceId(query.trace_id)}
                      getStatusBadge={getStatusBadge}
                    />
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function QueryRow({
  query,
  onViewDetails,
  getStatusBadge,
}: {
  query: QueryListItem;
  onViewDetails: () => void;
  getStatusBadge: (status?: QueryStatus) => React.ReactNode;
}) {
  // Poll status if query is pending or processing
  const liveStatus = usePollQueryStatus(
    query.status === 'pending' || query.status === 'processing' ? query.trace_id : null
  );

  const currentStatus = liveStatus?.status || query.status;

  return (
    <tr className="border-b border-gray-800 hover:bg-gray-800/50 transition-colors">
      <td className="py-3 px-4">
        <code className="text-sm text-blue-400">{query.trace_id}</code>
      </td>
      <td className="py-3 px-4 max-w-md">
        <div className="truncate text-gray-300">{query.query_text}</div>
      </td>
      <td className="py-3 px-4">{getStatusBadge(currentStatus as QueryStatus)}</td>
      <td className="py-3 px-4">
        {query.confidence ? (
          <span className="text-gray-300">{(query.confidence * 100).toFixed(1)}%</span>
        ) : (
          <span className="text-gray-500">-</span>
        )}
      </td>
      <td className="py-3 px-4 text-gray-400 text-sm">
        {new Date(query.timestamp).toLocaleString()}
      </td>
      <td className="py-3 px-4">
        <Button onClick={onViewDetails} variant="ghost" size="sm" className="flex items-center gap-1">
          <Eye className="w-4 h-4" />
          View
        </Button>
      </td>
    </tr>
  );
}
