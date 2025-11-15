/**
 * Progress Tracker - Real-time Ingestion Progress
 * =================================================
 *
 * Displays real-time progress of running ingestion batch.
 */

import React, { useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import {
  Activity,
  CheckCircle,
  XCircle,
  Clock,
  DollarSign,
  AlertTriangle,
  StopCircle,
  Database,
  GitBranch,
} from 'lucide-react';
import { Alert, AlertDescription } from '@/components/ui/alert';

// =============================================================================
// Types
// =============================================================================

interface IngestionBatchStatus {
  batch_id: string;
  batch_name?: string;
  status: string; // "running", "completed", "failed", "stopped"
  articles_requested: number;
  articles_fetched: number;
  articles_processed: number;
  current_article?: string;
  total_entities_extracted: number;
  entities_auto_approved: number;
  entities_manual_review: number;
  avg_entity_confidence: number;
  total_relationships_extracted: number;
  relationships_auto_approved: number;
  relationships_manual_review: number;
  avg_relationship_confidence: number;
  total_llm_cost_usd: number;
  elapsed_seconds?: number;
  estimated_completion_seconds?: number;
  errors_count: number;
  last_error?: string;
  started_at: string;
  completed_at?: string;
}

interface ProgressTrackerProps {
  batchId: string;
  onBatchCompleted?: () => void;
}

// =============================================================================
// API Functions
// =============================================================================

const fetchBatchStatus = async (batchId: string): Promise<IngestionBatchStatus> => {
  const response = await fetch(`http://localhost:8001/api/kg-ingestion/status/${batchId}`);
  if (!response.ok) throw new Error('Failed to fetch batch status');
  return response.json();
};

const stopBatch = async (batchId: string): Promise<void> => {
  const response = await fetch(`http://localhost:8001/api/kg-ingestion/stop/${batchId}`, {
    method: 'POST',
  });
  if (!response.ok) throw new Error('Failed to stop batch');
};

// =============================================================================
// Helper Functions
// =============================================================================

const formatDuration = (seconds?: number): string => {
  if (!seconds) return '--:--:--';
  const hours = Math.floor(seconds / 3600);
  const mins = Math.floor((seconds % 3600) / 60);
  const secs = Math.floor(seconds % 60);
  return `${hours.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
};

const getStatusBadge = (status: string) => {
  switch (status) {
    case 'running':
      return <Badge className="bg-blue-500"><Activity className="h-3 w-3 mr-1" />Running</Badge>;
    case 'completed':
      return <Badge className="bg-green-500"><CheckCircle className="h-3 w-3 mr-1" />Completed</Badge>;
    case 'failed':
      return <Badge className="bg-red-500"><XCircle className="h-3 w-3 mr-1" />Failed</Badge>;
    case 'stopped':
      return <Badge className="bg-yellow-500"><StopCircle className="h-3 w-3 mr-1" />Stopped</Badge>;
    default:
      return <Badge>{status}</Badge>;
  }
};

// =============================================================================
// Main Component
// =============================================================================

export const ProgressTracker: React.FC<ProgressTrackerProps> = ({
  batchId,
  onBatchCompleted,
}) => {
  // Poll batch status every 2 seconds
  const { data: status, isLoading, error, refetch } = useQuery({
    queryKey: ['batch-status', batchId],
    queryFn: () => fetchBatchStatus(batchId),
    refetchInterval: 2000, // Poll every 2 seconds
  });

  // Call onBatchCompleted when batch finishes
  useEffect(() => {
    if (status && ['completed', 'failed', 'stopped'].includes(status.status)) {
      onBatchCompleted?.();
    }
  }, [status?.status, onBatchCompleted]);

  const handleStop = async () => {
    if (confirm('Are you sure you want to stop this batch?')) {
      try {
        await stopBatch(batchId);
        refetch();
      } catch (err) {
        console.error('Failed to stop batch:', err);
      }
    }
  };

  if (isLoading) {
    return (
      <Card>
        <CardContent className="p-12 text-center">
          <Activity className="h-8 w-8 mx-auto mb-4 text-blue-500 animate-spin" />
          <p className="text-gray-600">Loading batch status...</p>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Alert className="border-red-400 bg-red-50">
        <AlertTriangle className="h-5 w-5 text-red-600" />
        <AlertDescription className="text-red-800">
          Failed to load batch status: {error.message}
        </AlertDescription>
      </Alert>
    );
  }

  if (!status) return null;

  const progress = status.articles_requested > 0
    ? (status.articles_processed / status.articles_requested) * 100
    : 0;

  return (
    <div className="space-y-6">
      {/* Header Card */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center">
                {getStatusBadge(status.status)}
                <span className="ml-3">
                  {status.batch_name || `Batch ${batchId.substring(0, 8)}`}
                </span>
              </CardTitle>
              <p className="text-sm text-gray-600 mt-1">
                Articles {status.articles_processed} / {status.articles_requested}
                {status.current_article && ` (Current: ${status.current_article})`}
              </p>
            </div>
            {status.status === 'running' && (
              <Button variant="destructive" onClick={handleStop}>
                <StopCircle className="h-4 w-4 mr-2" />
                Stop Batch
              </Button>
            )}
          </div>
        </CardHeader>
        <CardContent>
          {/* Progress Bar */}
          <div className="space-y-2">
            <Progress value={progress} className="h-3" />
            <div className="flex justify-between text-sm text-gray-600">
              <span>{progress.toFixed(1)}% Complete</span>
              <span>
                {status.elapsed_seconds !== undefined && (
                  <>
                    Elapsed: {formatDuration(status.elapsed_seconds)}
                    {status.estimated_completion_seconds !== undefined && (
                      <> • ETA: {formatDuration(status.estimated_completion_seconds)}</>
                    )}
                  </>
                )}
              </span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Statistics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Entities Card */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center">
              <Database className="h-4 w-4 mr-2 text-purple-600" />
              Entities Extracted
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-2xl font-bold">{status.total_entities_extracted}</span>
              <Badge variant="outline" className="text-xs">
                Avg Confidence: {status.avg_entity_confidence.toFixed(2)}
              </Badge>
            </div>

            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-600">Auto-approved:</span>
                <span className="font-semibold text-green-600">
                  {status.entities_auto_approved}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Manual review:</span>
                <span className="font-semibold text-yellow-600">
                  {status.entities_manual_review}
                </span>
              </div>
            </div>

            {/* Progress bar */}
            <div className="space-y-1">
              <div className="h-2 bg-gray-200 rounded overflow-hidden">
                <div
                  className="h-full bg-green-500"
                  style={{
                    width: `${status.total_entities_extracted > 0
                      ? (status.entities_auto_approved / status.total_entities_extracted) * 100
                      : 0
                    }%`,
                  }}
                />
              </div>
              <p className="text-xs text-gray-500">
                {status.total_entities_extracted > 0
                  ? ((status.entities_auto_approved / status.total_entities_extracted) * 100).toFixed(0)
                  : 0
                }% auto-approved
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Relationships Card */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center">
              <GitBranch className="h-4 w-4 mr-2 text-blue-600" />
              Relationships Extracted
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-2xl font-bold">{status.total_relationships_extracted}</span>
              <Badge variant="outline" className="text-xs">
                Avg Confidence: {status.avg_relationship_confidence.toFixed(2)}
              </Badge>
            </div>

            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-gray-600">Auto-approved:</span>
                <span className="font-semibold text-green-600">
                  {status.relationships_auto_approved}
                </span>
              </div>
              <div className="flex justify-between">
                <span className="text-gray-600">Manual review:</span>
                <span className="font-semibold text-yellow-600">
                  {status.relationships_manual_review}
                </span>
              </div>
            </div>

            {/* Progress bar */}
            <div className="space-y-1">
              <div className="h-2 bg-gray-200 rounded overflow-hidden">
                <div
                  className="h-full bg-green-500"
                  style={{
                    width: `${status.total_relationships_extracted > 0
                      ? (status.relationships_auto_approved / status.total_relationships_extracted) * 100
                      : 0
                    }%`,
                  }}
                />
              </div>
              <p className="text-xs text-gray-500">
                {status.total_relationships_extracted > 0
                  ? ((status.relationships_auto_approved / status.total_relationships_extracted) * 100).toFixed(0)
                  : 0
                }% auto-approved
              </p>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Cost & Errors */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Cost Card */}
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center">
                <DollarSign className="h-5 w-5 text-green-600 mr-2" />
                <span className="text-sm font-medium">Total LLM Cost</span>
              </div>
              <span className="text-xl font-bold text-green-600">
                ${status.total_llm_cost_usd.toFixed(4)}
              </span>
            </div>
          </CardContent>
        </Card>

        {/* Errors Card */}
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center">
                <AlertTriangle className="h-5 w-5 text-red-600 mr-2" />
                <span className="text-sm font-medium">Errors</span>
              </div>
              <span className="text-xl font-bold text-red-600">
                {status.errors_count}
              </span>
            </div>
            {status.last_error && (
              <p className="text-xs text-red-600 mt-2">{status.last_error}</p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Completion Message */}
      {status.status === 'completed' && (
        <Alert className="border-green-400 bg-green-50">
          <CheckCircle className="h-5 w-5 text-green-600" />
          <AlertDescription className="text-green-800">
            <strong>Batch Completed!</strong> Successfully processed {status.articles_processed} articles.
            Total cost: ${status.total_llm_cost_usd.toFixed(2)}
          </AlertDescription>
        </Alert>
      )}

      {status.status === 'failed' && (
        <Alert className="border-red-400 bg-red-50">
          <XCircle className="h-5 w-5 text-red-600" />
          <AlertDescription className="text-red-800">
            <strong>Batch Failed!</strong> {status.last_error || 'Unknown error'}
          </AlertDescription>
        </Alert>
      )}
    </div>
  );
};
