/**
 * StagingEntityList - Admin UI for reviewing ingestion staging queue
 *
 * Displays entities awaiting manual review from the ingestion pipeline.
 * Supports filtering by source, entity type, confidence score.
 */

import React, { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Loader2, CheckCircle, XCircle, AlertCircle } from 'lucide-react';
import { EntityReviewCard } from './EntityReviewCard';
import { ConfidenceScoreChart } from './ConfidenceScoreChart';

// =============================================================================
// Types
// =============================================================================

interface StagingEntity {
  id: number;
  entity_type: string;
  source_type: string;
  raw_data: {
    entity_type: string;
    properties: Record<string, any>;
    confidence: number;
    provenance: {
      source: string;
      source_url?: string;
      urn?: string;
    };
    relationships?: Array<{
      type: string;
      target_node: {
        entity_type: string;
        properties: Record<string, any>;
      };
    }>;
  };
  confidence_score: number;
  status: 'PENDING' | 'APPROVED' | 'REJECTED';
  created_at: string;
  reviewed_at?: string;
  reviewed_by?: string;
}

interface StatsData {
  total_pending: number;
  total_approved: number;
  total_rejected: number;
  avg_confidence: number;
  by_source: Record<string, number>;
  by_entity_type: Record<string, number>;
}

// =============================================================================
// API Functions
// =============================================================================

const fetchStagingEntities = async (
  status: string = 'PENDING',
  source?: string,
  limit: number = 100
): Promise<StagingEntity[]> => {
  const params = new URLSearchParams({ status, limit: String(limit) });
  if (source && source !== 'all') params.append('source_type', source);

  const response = await fetch(`/api/admin/staging-entities?${params}`);
  if (!response.ok) throw new Error('Failed to fetch staging entities');
  return response.json();
};

const fetchStagingStats = async (): Promise<StatsData> => {
  const response = await fetch('/api/admin/staging-entities/stats');
  if (!response.ok) throw new Error('Failed to fetch stats');
  return response.json();
};

const reviewEntity = async (id: number, approved: boolean, note?: string) => {
  const response = await fetch(`/api/admin/staging-entities/${id}/review`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ approved, note }),
  });
  if (!response.ok) throw new Error('Failed to review entity');
  return response.json();
};

const batchApprove = async (ids: number[]) => {
  const response = await fetch('/api/admin/staging-entities/batch-approve', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ids }),
  });
  if (!response.ok) throw new Error('Failed to batch approve');
  return response.json();
};

// =============================================================================
// Main Component
// =============================================================================

export const StagingEntityList: React.FC = () => {
  const queryClient = useQueryClient();

  // State
  const [selectedStatus, setSelectedStatus] = useState<string>('PENDING');
  const [selectedSource, setSelectedSource] = useState<string>('all');
  const [selectedEntities, setSelectedEntities] = useState<Set<number>>(new Set());
  const [currentEntityIndex, setCurrentEntityIndex] = useState<number>(0);

  // Queries
  const {
    data: entities,
    isLoading: entitiesLoading,
    error: entitiesError,
  } = useQuery({
    queryKey: ['staging-entities', selectedStatus, selectedSource],
    queryFn: () => fetchStagingEntities(selectedStatus, selectedSource),
  });

  const { data: stats, isLoading: statsLoading } = useQuery({
    queryKey: ['staging-stats'],
    queryFn: fetchStagingStats,
  });

  // Mutations
  const reviewMutation = useMutation({
    mutationFn: ({ id, approved, note }: { id: number; approved: boolean; note?: string }) =>
      reviewEntity(id, approved, note),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['staging-entities'] });
      queryClient.invalidateQueries({ queryKey: ['staging-stats'] });
      // Move to next entity
      if (entities && currentEntityIndex < entities.length - 1) {
        setCurrentEntityIndex(currentEntityIndex + 1);
      }
    },
  });

  const batchApproveMutation = useMutation({
    mutationFn: batchApprove,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['staging-entities'] });
      queryClient.invalidateQueries({ queryKey: ['staging-stats'] });
      setSelectedEntities(new Set());
    },
  });

  // Handlers
  const handleApprove = (id: number, note?: string) => {
    reviewMutation.mutate({ id, approved: true, note });
  };

  const handleReject = (id: number, note?: string) => {
    reviewMutation.mutate({ id, approved: false, note });
  };

  const handleBatchApprove = () => {
    if (selectedEntities.size > 0) {
      batchApproveMutation.mutate(Array.from(selectedEntities));
    }
  };

  const toggleEntitySelection = (id: number) => {
    const newSelection = new Set(selectedEntities);
    if (newSelection.has(id)) {
      newSelection.delete(id);
    } else {
      newSelection.add(id);
    }
    setSelectedEntities(newSelection);
  };

  // Current entity for review
  const currentEntity = entities?.[currentEntityIndex];

  // Loading state
  if (entitiesLoading || statsLoading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="h-8 w-8 animate-spin text-gray-400" />
        <span className="ml-2 text-gray-600">Loading staging queue...</span>
      </div>
    );
  }

  // Error state
  if (entitiesError) {
    return (
      <Card className="border-red-200 bg-red-50">
        <CardContent className="pt-6">
          <div className="flex items-center text-red-600">
            <AlertCircle className="h-5 w-5 mr-2" />
            <span>Error loading staging entities: {(entitiesError as Error).message}</span>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header with Stats */}
      <Card>
        <CardHeader>
          <CardTitle>Ingestion Review Queue</CardTitle>
          <CardDescription>
            Review entities from the multi-source ingestion pipeline
          </CardDescription>
        </CardHeader>
        <CardContent>
          {stats && (
            <div className="grid grid-cols-4 gap-4 mb-6">
              <div className="text-center">
                <div className="text-2xl font-bold text-yellow-600">{stats.total_pending}</div>
                <div className="text-sm text-gray-600">Pending</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-green-600">{stats.total_approved}</div>
                <div className="text-sm text-gray-600">Approved</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-red-600">{stats.total_rejected}</div>
                <div className="text-sm text-gray-600">Rejected</div>
              </div>
              <div className="text-center">
                <div className="text-2xl font-bold text-blue-600">
                  {stats.avg_confidence.toFixed(2)}
                </div>
                <div className="text-sm text-gray-600">Avg Confidence</div>
              </div>
            </div>
          )}

          {/* Filters */}
          <div className="flex gap-4 items-center">
            <div className="flex-1">
              <label className="block text-sm font-medium text-gray-700 mb-1">Status</label>
              <Select value={selectedStatus} onValueChange={setSelectedStatus}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="PENDING">Pending</SelectItem>
                  <SelectItem value="APPROVED">Approved</SelectItem>
                  <SelectItem value="REJECTED">Rejected</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="flex-1">
              <label className="block text-sm font-medium text-gray-700 mb-1">Source</label>
              <Select value={selectedSource} onValueChange={setSelectedSource}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Sources</SelectItem>
                  <SelectItem value="VISUALEX">visualex</SelectItem>
                  <SelectItem value="DOCUMENTS">Documents (PDF/LLM)</SelectItem>
                  <SelectItem value="COMMUNITY">Community</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {selectedEntities.size > 0 && (
              <div className="flex-1">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Batch Actions
                </label>
                <Button
                  onClick={handleBatchApprove}
                  disabled={batchApproveMutation.isPending}
                  className="w-full"
                >
                  {batchApproveMutation.isPending ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      Approving...
                    </>
                  ) : (
                    <>
                      <CheckCircle className="h-4 w-4 mr-2" />
                      Approve {selectedEntities.size} Selected
                    </>
                  )}
                </Button>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Confidence Distribution Chart */}
      {entities && entities.length > 0 && (
        <ConfidenceScoreChart entities={entities} />
      )}

      {/* Current Entity Review */}
      {currentEntity ? (
        <div className="space-y-4">
          <div className="flex justify-between items-center">
            <h3 className="text-lg font-semibold">
              Reviewing Entity {currentEntityIndex + 1} of {entities?.length || 0}
            </h3>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setCurrentEntityIndex(Math.max(0, currentEntityIndex - 1))}
                disabled={currentEntityIndex === 0}
              >
                Previous
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() =>
                  setCurrentEntityIndex(
                    Math.min((entities?.length || 1) - 1, currentEntityIndex + 1)
                  )
                }
                disabled={currentEntityIndex === (entities?.length || 1) - 1}
              >
                Next
              </Button>
            </div>
          </div>

          <EntityReviewCard
            entity={currentEntity}
            onApprove={handleApprove}
            onReject={handleReject}
            isReviewing={reviewMutation.isPending}
          />
        </div>
      ) : (
        <Card>
          <CardContent className="pt-6 text-center text-gray-500">
            {selectedStatus === 'PENDING' ? (
              <div>
                <CheckCircle className="h-12 w-12 mx-auto mb-2 text-green-400" />
                <p className="font-medium">No pending entities!</p>
                <p className="text-sm">All entities have been reviewed.</p>
              </div>
            ) : (
              <p>No entities found with selected filters.</p>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
};
