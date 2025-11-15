/**
 * Batch Configuration Form
 * =========================
 *
 * Form to configure LLM ingestion batch parameters.
 */

import React, { useState, useEffect } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Slider } from '@/components/ui/slider';
import { Switch } from '@/components/ui/switch';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Loader2, Sparkles, DollarSign, AlertTriangle } from 'lucide-react';

// =============================================================================
// Types
// =============================================================================

interface AvailableModel {
  model_id: string;
  provider: string;
  name: string;
  description: string;
  cost_per_1m_input: number;
  cost_per_1m_output: number;
  recommended: boolean;
}

interface IngestionBatchConfig {
  batch_name?: string;
  tipo_atto: string;
  start_article: number;
  end_article: number;
  llm_model: string;
  llm_temperature: number;
  include_brocardi: boolean;
  entity_auto_approve_threshold: number;
  relationship_auto_approve_threshold: number;
  dry_run: boolean;
  max_concurrent_llm: number;
}

interface BatchConfigFormProps {
  onBatchStarted: (batchId: string) => void;
}

// =============================================================================
// API Functions
// =============================================================================

const fetchAvailableModels = async (): Promise<AvailableModel[]> => {
  const response = await fetch('http://localhost:8001/api/kg-ingestion/models');
  if (!response.ok) throw new Error('Failed to fetch models');
  return response.json();
};

const startIngestionBatch = async (config: IngestionBatchConfig): Promise<{ batch_id: string }> => {
  const response = await fetch('http://localhost:8001/api/kg-ingestion/start', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config),
  });
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to start batch');
  }
  return response.json();
};

// =============================================================================
// Main Component
// =============================================================================

export const BatchConfigForm: React.FC<BatchConfigFormProps> = ({ onBatchStarted }) => {
  // Form state
  const [batchName, setBatchName] = useState('');
  const [startArticle, setStartArticle] = useState(2043);
  const [endArticle, setEndArticle] = useState(2045);
  const [selectedModel, setSelectedModel] = useState('google/gemini-2.5-flash');
  const [temperature, setTemperature] = useState(0.1);
  const [includeBrocardi, setIncludeBrocardi] = useState(true);
  const [entityThreshold, setEntityThreshold] = useState(0.85);
  const [relationshipThreshold, setRelationshipThreshold] = useState(0.80);
  const [dryRun, setDryRun] = useState(false);
  const [maxConcurrent, setMaxConcurrent] = useState(3);

  // Fetch available models
  const { data: models, isLoading: modelsLoading } = useQuery({
    queryKey: ['available-models'],
    queryFn: fetchAvailableModels,
  });

  // Start batch mutation
  const startBatchMutation = useMutation({
    mutationFn: startIngestionBatch,
    onSuccess: (data) => {
      onBatchStarted(data.batch_id);
    },
  });

  // Calculate cost estimation
  const estimateCost = () => {
    if (!models) return 0;
    const model = models.find((m) => m.model_id === selectedModel);
    if (!model) return 0;

    const numArticles = endArticle - startArticle + 1;
    const avgInputTokens = 2000; // Article text + BrocardiInfo + prompt
    const avgOutputTokens = 1500; // Entities + relationships JSON

    const totalInputTokens = numArticles * avgInputTokens;
    const totalOutputTokens = numArticles * avgOutputTokens;

    const inputCost = (totalInputTokens / 1_000_000) * model.cost_per_1m_input;
    const outputCost = (totalOutputTokens / 1_000_000) * model.cost_per_1m_output;

    return inputCost + outputCost;
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    const config: IngestionBatchConfig = {
      batch_name: batchName || undefined,
      tipo_atto: 'codice civile',
      start_article: startArticle,
      end_article: endArticle,
      llm_model: selectedModel,
      llm_temperature: temperature,
      include_brocardi: includeBrocardi,
      entity_auto_approve_threshold: entityThreshold,
      relationship_auto_approve_threshold: relationshipThreshold,
      dry_run: dryRun,
      max_concurrent_llm: maxConcurrent,
    };

    startBatchMutation.mutate(config);
  };

  const isValid = startArticle > 0 && endArticle > 0 && startArticle <= endArticle && endArticle <= 2969;

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* Batch Name */}
      <div>
        <Label htmlFor="batch-name">Batch Name (Optional)</Label>
        <Input
          id="batch-name"
          placeholder="e.g., Responsabilità civile (Art. 2043-2059)"
          value={batchName}
          onChange={(e) => setBatchName(e.target.value)}
          className="mt-1"
        />
      </div>

      {/* Article Range */}
      <div className="grid grid-cols-2 gap-4">
        <div>
          <Label htmlFor="start-article">Start Article *</Label>
          <Input
            id="start-article"
            type="number"
            min={1}
            max={2969}
            value={startArticle}
            onChange={(e) => setStartArticle(Number(e.target.value))}
            className="mt-1"
            required
          />
        </div>
        <div>
          <Label htmlFor="end-article">End Article *</Label>
          <Input
            id="end-article"
            type="number"
            min={1}
            max={2969}
            value={endArticle}
            onChange={(e) => setEndArticle(Number(e.target.value))}
            className="mt-1"
            required
          />
        </div>
      </div>

      {!isValid && (
        <Alert className="border-red-400 bg-red-50">
          <AlertTriangle className="h-4 w-4 text-red-600" />
          <AlertDescription className="text-red-800 text-sm">
            Invalid article range. Must be 1-2969, and start ≤ end.
          </AlertDescription>
        </Alert>
      )}

      {/* LLM Model Selection */}
      <div>
        <Label htmlFor="llm-model">LLM Model *</Label>
        {modelsLoading ? (
          <div className="flex items-center mt-2 text-gray-500">
            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            Loading models...
          </div>
        ) : (
          <Select value={selectedModel} onValueChange={setSelectedModel}>
            <SelectTrigger className="mt-1">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {models?.map((model) => (
                <SelectItem key={model.model_id} value={model.model_id}>
                  <div className="flex items-center">
                    {model.recommended && (
                      <Sparkles className="h-3 w-3 mr-2 text-yellow-500" />
                    )}
                    <span className="font-medium">{model.name}</span>
                    <span className="ml-2 text-xs text-gray-500">
                      (${model.cost_per_1m_input}/${model.cost_per_1m_output} per 1M tokens)
                    </span>
                  </div>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}
        {models && (
          <p className="text-xs text-gray-600 mt-1">
            {models.find((m) => m.model_id === selectedModel)?.description}
          </p>
        )}
      </div>

      {/* Temperature */}
      <div>
        <Label htmlFor="temperature">
          Temperature: <span className="font-mono text-sm">{temperature.toFixed(2)}</span>
        </Label>
        <Slider
          id="temperature"
          min={0}
          max={2}
          step={0.1}
          value={[temperature]}
          onValueChange={(values) => setTemperature(values[0])}
          className="mt-2"
        />
        <p className="text-xs text-gray-600 mt-1">
          Lower = more consistent, Higher = more creative (recommended: 0.1-0.3 for extraction)
        </p>
      </div>

      {/* BrocardiInfo Toggle */}
      <div className="flex items-center justify-between p-4 bg-gray-50 rounded">
        <div>
          <Label htmlFor="include-brocardi" className="text-base">
            Include BrocardiInfo Enrichment
          </Label>
          <p className="text-xs text-gray-600">
            Adds doctrinal data (brocardi, ratio, spiegazione, massime)
          </p>
        </div>
        <Switch
          id="include-brocardi"
          checked={includeBrocardi}
          onCheckedChange={setIncludeBrocardi}
        />
      </div>

      {/* Auto-Approval Thresholds */}
      <div className="space-y-4 p-4 bg-blue-50 rounded border border-blue-200">
        <h4 className="font-semibold text-sm text-blue-900">Auto-Approval Thresholds</h4>

        <div>
          <Label htmlFor="entity-threshold">
            Entity Threshold: <span className="font-mono text-sm">{entityThreshold.toFixed(2)}</span>
          </Label>
          <Slider
            id="entity-threshold"
            min={0}
            max={1}
            step={0.05}
            value={[entityThreshold]}
            onValueChange={(values) => setEntityThreshold(values[0])}
            className="mt-2"
          />
        </div>

        <div>
          <Label htmlFor="relationship-threshold">
            Relationship Threshold: <span className="font-mono text-sm">{relationshipThreshold.toFixed(2)}</span>
          </Label>
          <Slider
            id="relationship-threshold"
            min={0}
            max={1}
            step={0.05}
            value={[relationshipThreshold]}
            onValueChange={(values) => setRelationshipThreshold(values[0])}
            className="mt-2"
          />
        </div>

        <p className="text-xs text-blue-800">
          Entities/relationships above these thresholds are auto-approved. Lower values = more manual review.
        </p>
      </div>

      {/* Advanced Options */}
      <div className="grid grid-cols-2 gap-4">
        <div className="flex items-center justify-between p-4 bg-gray-50 rounded">
          <div>
            <Label htmlFor="dry-run" className="text-base">
              Dry Run Mode
            </Label>
            <p className="text-xs text-gray-600">No database writes</p>
          </div>
          <Switch id="dry-run" checked={dryRun} onCheckedChange={setDryRun} />
        </div>

        <div>
          <Label htmlFor="max-concurrent">Max Concurrent LLM Calls</Label>
          <Input
            id="max-concurrent"
            type="number"
            min={1}
            max={10}
            value={maxConcurrent}
            onChange={(e) => setMaxConcurrent(Number(e.target.value))}
            className="mt-1"
          />
        </div>
      </div>

      {/* Cost Estimation */}
      <Alert className="border-green-400 bg-green-50">
        <DollarSign className="h-4 w-4 text-green-600" />
        <AlertDescription className="text-green-800">
          <strong>Estimated Cost:</strong> ${estimateCost().toFixed(2)} USD
          <span className="text-xs ml-2">
            ({endArticle - startArticle + 1} articles × avg tokens)
          </span>
        </AlertDescription>
      </Alert>

      {/* Error Display */}
      {startBatchMutation.isError && (
        <Alert className="border-red-400 bg-red-50">
          <AlertTriangle className="h-4 w-4 text-red-600" />
          <AlertDescription className="text-red-800">
            {startBatchMutation.error?.message || 'Failed to start batch'}
          </AlertDescription>
        </Alert>
      )}

      {/* Submit Button */}
      <Button
        type="submit"
        className="w-full"
        size="lg"
        disabled={!isValid || startBatchMutation.isPending}
      >
        {startBatchMutation.isPending ? (
          <>
            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            Starting Batch...
          </>
        ) : (
          <>
            <Sparkles className="h-4 w-4 mr-2" />
            Start Ingestion Batch
          </>
        )}
      </Button>
    </form>
  );
};
