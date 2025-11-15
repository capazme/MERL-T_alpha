/**
 * Batch History - List of Previous Ingestion Batches
 * ====================================================
 *
 * Displays historical ingestion batches with filtering and stats.
 */

import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  CheckCircle,
  XCircle,
  Clock,
  Activity,
  StopCircle,
  DollarSign,
  Database,
  GitBranch,
  ExternalLink,
} from 'lucide-react';
import { Alert, AlertDescription } from '@/components/ui/alert';

// =============================================================================
// Types
// =============================================================================

interface BatchHistoryItem {
  batch_id: string;
  batch_name?: string;
  config: {
    start_article: number;
    end_article: number;
    llm_model: string;
    include_brocardi: boolean;
    dry_run: boolean;
  };
  stats: {
    articles: {
      requested: number;
      fetched: number;
      processed: number;
    };
    entities: {
      total_extracted: number;
      auto_approved: number;
      manual_review: number;
      avg_confidence: number;
    };
    relationships: {
      total_extracted: number;
      auto_approved: number;
      manual_review: number;
      avg_confidence: number;
    };
    cost_usd: number;
    errors_count: number;
  };
  status: string;
  started_at: string;
  completed_at?: string;
}

// =============================================================================
// API Functions
// =============================================================================

const fetchBatchHistory = async (
  status?: string
): Promise<BatchHistoryItem[]> => {
  const url = new URL('http://localhost:8001/api/kg-ingestion/batches');
  if (status) {
    url.searchParams.append('status', status);
  }
  const response = await fetch(url.toString());
  if (!response.ok) throw new Error('Failed to fetch batch history');
  return response.json();
};

// =============================================================================
// Helper Functions
// =============================================================================

const formatDate = (dateStr: string): string => {
  const date = new Date(dateStr);
  return date.toLocaleString('it-IT', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
};

const getStatusIcon = (status: string) => {
  switch (status) {
    case 'running':
      return <Activity className="h-4 w-4 text-blue-500" />;
    case 'completed':
      return <CheckCircle className="h-4 w-4 text-green-500" />;
    case 'failed':
      return <XCircle className="h-4 w-4 text-red-500" />;
    case 'stopped':
      return <StopCircle className="h-4 w-4 text-yellow-500" />;
    default:
      return <Clock className="h-4 w-4 text-gray-500" />;
  }
};

const getStatusBadge = (status: string) => {
  switch (status) {
    case 'running':
      return <Badge className="bg-blue-500">Running</Badge>;
    case 'completed':
      return <Badge className="bg-green-500">Completed</Badge>;
    case 'failed':
      return <Badge className="bg-red-500">Failed</Badge>;
    case 'stopped':
      return <Badge className="bg-yellow-500">Stopped</Badge>;
    default:
      return <Badge>{status}</Badge>;
  }
};

// =============================================================================
// Main Component
// =============================================================================

export const BatchHistory: React.FC = () => {
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [expandedBatchId, setExpandedBatchId] = useState<string | null>(null);

  const { data: batches, isLoading, error, refetch } = useQuery({
    queryKey: ['batch-history', statusFilter],
    queryFn: () =>
      fetchBatchHistory(statusFilter === 'all' ? undefined : statusFilter),
    refetchInterval: 5000, // Refresh every 5 seconds
  });

  if (isLoading) {
    return (
      <Card>
        <CardContent className="p-12 text-center">
          <Activity className="h-8 w-8 mx-auto mb-4 text-blue-500 animate-spin" />
          <p className="text-gray-600">Loading batch history...</p>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Alert className="border-red-400 bg-red-50">
        <XCircle className="h-5 w-5 text-red-600" />
        <AlertDescription className="text-red-800">
          Failed to load batch history: {error.message}
        </AlertDescription>
      </Alert>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Ingestion Batch History</CardTitle>
            <div className="flex items-center space-x-4">
              {/* Status Filter */}
              <Select value={statusFilter} onValueChange={setStatusFilter}>
                <SelectTrigger className="w-40">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Status</SelectItem>
                  <SelectItem value="running">Running</SelectItem>
                  <SelectItem value="completed">Completed</SelectItem>
                  <SelectItem value="failed">Failed</SelectItem>
                  <SelectItem value="stopped">Stopped</SelectItem>
                </SelectContent>
              </Select>

              <Button variant="outline" size="sm" onClick={() => refetch()}>
                Refresh
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {batches && batches.length === 0 ? (
            <div className="text-center py-12 text-gray-500">
              No batches found. Start your first ingestion batch!
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-12"></TableHead>
                  <TableHead>Batch</TableHead>
                  <TableHead>Articles</TableHead>
                  <TableHead>Model</TableHead>
                  <TableHead>Entities</TableHead>
                  <TableHead>Relationships</TableHead>
                  <TableHead>Cost</TableHead>
                  <TableHead>Started</TableHead>
                  <TableHead className="w-12"></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {batches?.map((batch) => (
                  <React.Fragment key={batch.batch_id}>
                    {/* Main Row */}
                    <TableRow
                      className="cursor-pointer hover:bg-gray-50"
                      onClick={() =>
                        setExpandedBatchId(
                          expandedBatchId === batch.batch_id
                            ? null
                            : batch.batch_id
                        )
                      }
                    >
                      <TableCell>{getStatusIcon(batch.status)}</TableCell>
                      <TableCell>
                        <div>
                          <div className="font-medium">
                            {batch.batch_name || `Batch ${batch.batch_id.substring(0, 8)}`}
                          </div>
                          <div className="text-xs text-gray-500">
                            {batch.batch_id.substring(0, 13)}...
                          </div>
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="text-sm">
                          {batch.config.start_article} - {batch.config.end_article}
                        </div>
                        <div className="text-xs text-gray-500">
                          ({batch.stats.articles.processed}/{batch.stats.articles.requested} processed)
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="text-xs">
                          {batch.config.llm_model.split('/')[1] || batch.config.llm_model}
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="text-sm font-medium">
                          {batch.stats.entities.total_extracted}
                        </div>
                        <div className="text-xs text-gray-500">
                          {batch.stats.entities.auto_approved} auto /
                          {batch.stats.entities.manual_review} manual
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="text-sm font-medium">
                          {batch.stats.relationships.total_extracted}
                        </div>
                        <div className="text-xs text-gray-500">
                          {batch.stats.relationships.auto_approved} auto /
                          {batch.stats.relationships.manual_review} manual
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="text-sm font-medium text-green-600">
                          ${batch.stats.cost_usd.toFixed(2)}
                        </div>
                      </TableCell>
                      <TableCell>
                        <div className="text-xs text-gray-600">
                          {formatDate(batch.started_at)}
                        </div>
                      </TableCell>
                      <TableCell>
                        {getStatusBadge(batch.status)}
                      </TableCell>
                    </TableRow>

                    {/* Expanded Details */}
                    {expandedBatchId === batch.batch_id && (
                      <TableRow>
                        <TableCell colSpan={9} className="bg-gray-50">
                          <div className="p-4 space-y-4">
                            {/* Configuration */}
                            <div>
                              <h4 className="font-semibold text-sm mb-2">Configuration</h4>
                              <div className="grid grid-cols-4 gap-4 text-xs">
                                <div>
                                  <span className="text-gray-600">LLM Model:</span>
                                  <div className="font-mono">{batch.config.llm_model}</div>
                                </div>
                                <div>
                                  <span className="text-gray-600">BrocardiInfo:</span>
                                  <div>{batch.config.include_brocardi ? 'Yes' : 'No'}</div>
                                </div>
                                <div>
                                  <span className="text-gray-600">Dry Run:</span>
                                  <div>{batch.config.dry_run ? 'Yes' : 'No'}</div>
                                </div>
                                <div>
                                  <span className="text-gray-600">Errors:</span>
                                  <div className="text-red-600">{batch.stats.errors_count}</div>
                                </div>
                              </div>
                            </div>

                            {/* Detailed Stats */}
                            <div>
                              <h4 className="font-semibold text-sm mb-2">Detailed Statistics</h4>
                              <div className="grid grid-cols-2 gap-4">
                                <div className="bg-white p-3 rounded border">
                                  <div className="flex items-center mb-2">
                                    <Database className="h-4 w-4 text-purple-600 mr-2" />
                                    <span className="font-semibold text-sm">Entities</span>
                                  </div>
                                  <div className="text-xs space-y-1">
                                    <div className="flex justify-between">
                                      <span>Total:</span>
                                      <span className="font-semibold">
                                        {batch.stats.entities.total_extracted}
                                      </span>
                                    </div>
                                    <div className="flex justify-between">
                                      <span>Auto-approved:</span>
                                      <span className="text-green-600">
                                        {batch.stats.entities.auto_approved}
                                      </span>
                                    </div>
                                    <div className="flex justify-between">
                                      <span>Manual review:</span>
                                      <span className="text-yellow-600">
                                        {batch.stats.entities.manual_review}
                                      </span>
                                    </div>
                                    <div className="flex justify-between">
                                      <span>Avg Confidence:</span>
                                      <span className="font-mono">
                                        {batch.stats.entities.avg_confidence.toFixed(2)}
                                      </span>
                                    </div>
                                  </div>
                                </div>

                                <div className="bg-white p-3 rounded border">
                                  <div className="flex items-center mb-2">
                                    <GitBranch className="h-4 w-4 text-blue-600 mr-2" />
                                    <span className="font-semibold text-sm">Relationships</span>
                                  </div>
                                  <div className="text-xs space-y-1">
                                    <div className="flex justify-between">
                                      <span>Total:</span>
                                      <span className="font-semibold">
                                        {batch.stats.relationships.total_extracted}
                                      </span>
                                    </div>
                                    <div className="flex justify-between">
                                      <span>Auto-approved:</span>
                                      <span className="text-green-600">
                                        {batch.stats.relationships.auto_approved}
                                      </span>
                                    </div>
                                    <div className="flex justify-between">
                                      <span>Manual review:</span>
                                      <span className="text-yellow-600">
                                        {batch.stats.relationships.manual_review}
                                      </span>
                                    </div>
                                    <div className="flex justify-between">
                                      <span>Avg Confidence:</span>
                                      <span className="font-mono">
                                        {batch.stats.relationships.avg_confidence.toFixed(2)}
                                      </span>
                                    </div>
                                  </div>
                                </div>
                              </div>
                            </div>

                            {/* Actions */}
                            <div className="flex justify-end space-x-2">
                              <Button variant="outline" size="sm">
                                <ExternalLink className="h-3 w-3 mr-1" />
                                View in Review Dashboard
                              </Button>
                            </div>
                          </div>
                        </TableCell>
                      </TableRow>
                    )}
                  </React.Fragment>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
};
