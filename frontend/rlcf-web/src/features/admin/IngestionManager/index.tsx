/**
 * Ingestion Manager - Main Interface
 * ====================================
 *
 * Control panel for LLM-driven knowledge graph ingestion.
 *
 * Features:
 * - Configure ingestion batches (articles, model, thresholds)
 * - Start/stop batches
 * - Real-time progress tracking
 * - Historical batches view
 * - Cost estimation
 *
 * Usage:
 *   <Route path="/admin/ingestion" element={<IngestionManager />} />
 */

import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { AlertCircle, Database, Activity, History } from 'lucide-react';
import { Alert, AlertDescription } from '@/components/ui/alert';

import { BatchConfigForm } from './BatchConfigForm';
import { ProgressTracker } from './ProgressTracker';
import { BatchHistory } from './BatchHistory';

// =============================================================================
// Main Component
// =============================================================================

export const IngestionManager: React.FC = () => {
  const [activeBatchId, setActiveBatchId] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<string>('configure');

  const handleBatchStarted = (batchId: string) => {
    setActiveBatchId(batchId);
    setActiveTab('progress');
  };

  const handleBatchCompleted = () => {
    setActiveBatchId(null);
    setActiveTab('history');
  };

  return (
    <div className="container mx-auto p-6 max-w-7xl">
      {/* Header */}
      <div className="mb-8">
        <div className="flex items-center mb-2">
          <Database className="h-8 w-8 text-blue-600 mr-3" />
          <h1 className="text-3xl font-bold text-gray-900">
            Knowledge Graph Ingestion
          </h1>
        </div>
        <p className="text-gray-600">
          LLM-driven entity and relationship extraction from legal documents
        </p>
      </div>

      {/* Warning: Migration Required */}
      <Alert className="mb-6 border-yellow-400 bg-yellow-50">
        <AlertCircle className="h-5 w-5 text-yellow-600" />
        <AlertDescription className="text-yellow-800">
          <strong>Database Migration Required:</strong> Before running ingestion, apply the migration:
          <code className="block mt-2 bg-yellow-100 p-2 rounded text-sm">
            psql -U user -d merl_t {'<'} backend/preprocessing/migrations/001_create_kg_staging_tables.sql
          </code>
        </AlertDescription>
      </Alert>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-3 mb-6">
          <TabsTrigger value="configure" className="flex items-center">
            <Database className="h-4 w-4 mr-2" />
            Configure Batch
          </TabsTrigger>
          <TabsTrigger value="progress" className="flex items-center" disabled={!activeBatchId}>
            <Activity className="h-4 w-4 mr-2" />
            Progress
          </TabsTrigger>
          <TabsTrigger value="history" className="flex items-center">
            <History className="h-4 w-4 mr-2" />
            Batch History
          </TabsTrigger>
        </TabsList>

        {/* Configure Tab */}
        <TabsContent value="configure">
          <Card>
            <CardHeader>
              <CardTitle>Configure Ingestion Batch</CardTitle>
            </CardHeader>
            <CardContent>
              <BatchConfigForm onBatchStarted={handleBatchStarted} />
            </CardContent>
          </Card>
        </TabsContent>

        {/* Progress Tab */}
        <TabsContent value="progress">
          {activeBatchId ? (
            <ProgressTracker
              batchId={activeBatchId}
              onBatchCompleted={handleBatchCompleted}
            />
          ) : (
            <Card>
              <CardContent className="p-12 text-center text-gray-500">
                No active batch. Configure and start a batch to see progress.
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* History Tab */}
        <TabsContent value="history">
          <BatchHistory />
        </TabsContent>
      </Tabs>
    </div>
  );
};

export default IngestionManager;
