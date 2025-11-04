import React, { useState, useMemo } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { Badge } from '../../components/ui/Badge';
import { apiClient } from '../../lib/api';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import type { LegalTask, ExportFormat, DatasetMetrics } from '../../types';

interface ExportOptions {
  format: ExportFormat;
  includeMetadata: boolean;
  includeReasoning: boolean;
  includeUncertainty: boolean;
  anonymizeUsers: boolean;
  taskTypes: string[];
  minAuthorityScore: number;
  dateRange: {
    start: string | null;
    end: string | null;
  };
}

interface ExportPreview {
  totalTasks: number;
  totalFeedback: number;
  avgAuthorityScore: number;
  taskTypeDistribution: { type: string; count: number }[];
  qualityMetrics: {
    avgAccuracy: number;
    avgUtility: number;
    avgTransparency: number;
  };
  uncertaintyDistribution: { level: string; count: number }[];
}

const EXPORT_FORMATS = [
  {
    id: 'sft' as ExportFormat,
    name: 'Supervised Fine-Tuning (SFT)',
    description: 'Standard format for supervised learning with input-output pairs',
    icon: '🎯',
    fileExtension: 'jsonl',
    useCase: 'Training models on validated expert responses'
  },
  {
    id: 'preference' as ExportFormat,
    name: 'Preference Learning',
    description: 'Comparative format for RLHF/DPO training',
    icon: '⚖️',
    fileExtension: 'jsonl',
    useCase: 'Training reward models and preference optimization'
  },
  {
    id: 'research' as ExportFormat,
    name: 'Research Dataset',
    description: 'Comprehensive format with full metadata for analysis',
    icon: '📊',
    fileExtension: 'json',
    useCase: 'Academic research and uncertainty analysis'
  },
  {
    id: 'csv' as ExportFormat,
    name: 'CSV Export',
    description: 'Tabular format for statistical analysis',
    icon: '📈',
    fileExtension: 'csv',
    useCase: 'Statistical analysis and visualization'
  }
];

const QUALITY_COLORS = ['#8B5CF6', '#06D6A0', '#FFB500'];

export function ExportHub() {
  const [selectedFormat, setSelectedFormat] = useState<ExportFormat>('sft');
  const [exportOptions, setExportOptions] = useState<ExportOptions>({
    format: 'sft',
    includeMetadata: true,
    includeReasoning: true,
    includeUncertainty: false,
    anonymizeUsers: true,
    taskTypes: [],
    minAuthorityScore: 0,
    dateRange: { start: null, end: null }
  });
  const [showPreview, setShowPreview] = useState(false);

  // Fetch available task types
  const { data: taskTypes } = useQuery({
    queryKey: ['task-types'],
    queryFn: () => apiClient.tasks.getTaskTypes()
  });

  // Fetch dataset metrics for preview
  const { data: datasetMetrics, isLoading: loadingMetrics } = useQuery({
    queryKey: ['dataset-metrics', exportOptions],
    queryFn: () => apiClient.export.getDatasetMetrics(exportOptions),
    enabled: showPreview
  });

  // Export mutation
  const exportMutation = useMutation({
    mutationFn: (options: ExportOptions) => apiClient.export.generateDataset(options),
    onSuccess: (data) => {
      // Create download link
      const blob = new Blob([data.content], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = data.filename;
      document.body.appendChild(a);
      a.click();
      URL.revokeObjectURL(url);
      document.body.removeChild(a);
    },
    onError: (error: any) => {
      alert(`Export failed: ${error.message}`);
    }
  });

  const handleExportOptionChange = (key: keyof ExportOptions, value: any) => {
    setExportOptions(prev => ({
      ...prev,
      [key]: value,
      ...(key === 'format' && { format: value as ExportFormat })
    }));
  };

  const handleTaskTypeToggle = (taskType: string) => {
    setExportOptions(prev => ({
      ...prev,
      taskTypes: prev.taskTypes.includes(taskType)
        ? prev.taskTypes.filter(t => t !== taskType)
        : [...prev.taskTypes, taskType]
    }));
  };

  const selectedFormatInfo = EXPORT_FORMATS.find(f => f.id === selectedFormat);
  const estimatedFileSize = useMemo(() => {
    if (!datasetMetrics) return 'Unknown';
    const avgRecordSize = selectedFormat === 'csv' ? 0.5 : 2; // KB per record
    const totalRecords = datasetMetrics.totalTasks * (datasetMetrics.totalFeedback / datasetMetrics.totalTasks);
    return `${(totalRecords * avgRecordSize / 1024).toFixed(1)} MB`;
  }, [datasetMetrics, selectedFormat]);

  const canExport = exportOptions.taskTypes.length > 0 || exportOptions.minAuthorityScore >= 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-white mb-2">📦 RLCF Dataset Export Hub</h1>
        <p className="text-slate-400">
          Generate high-quality datasets from community-validated legal AI responses
        </p>
      </div>

      {/* Export Format Selection */}
      <Card className="border-purple-700">
        <CardHeader>
          <CardTitle>🎯 Select Export Format</CardTitle>
          <p className="text-slate-400">Choose the format that best fits your use case</p>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {EXPORT_FORMATS.map((format) => (
              <div
                key={format.id}
                className={`p-4 rounded-lg border cursor-pointer transition-all ${
                  selectedFormat === format.id
                    ? 'border-purple-500 bg-purple-950/20'
                    : 'border-slate-700 hover:border-slate-600'
                }`}
                onClick={() => {
                  setSelectedFormat(format.id);
                  handleExportOptionChange('format', format.id);
                }}
              >
                <div className="text-2xl mb-2">{format.icon}</div>
                <h4 className="font-semibold text-slate-200 mb-1">{format.name}</h4>
                <p className="text-sm text-slate-400 mb-2">{format.description}</p>
                <Badge variant="outline" className="text-xs">
                  .{format.fileExtension}
                </Badge>
                <p className="text-xs text-slate-500 mt-2">{format.useCase}</p>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Export Configuration */}
        <Card className="border-slate-700">
          <CardHeader>
            <CardTitle>⚙️ Export Configuration</CardTitle>
            <p className="text-slate-400">Customize your dataset export</p>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Content Options */}
            <div>
              <h4 className="font-semibold text-slate-200 mb-3">Content Options</h4>
              <div className="space-y-3">
                <label className="flex items-center gap-3">
                  <input
                    type="checkbox"
                    checked={exportOptions.includeMetadata}
                    onChange={(e) => handleExportOptionChange('includeMetadata', e.target.checked)}
                    className="rounded"
                  />
                  <span className="text-slate-300">Include metadata (timestamps, authority scores)</span>
                </label>
                <label className="flex items-center gap-3">
                  <input
                    type="checkbox"
                    checked={exportOptions.includeReasoning}
                    onChange={(e) => handleExportOptionChange('includeReasoning', e.target.checked)}
                    className="rounded"
                  />
                  <span className="text-slate-300">Include expert reasoning and justifications</span>
                </label>
                <label className="flex items-center gap-3">
                  <input
                    type="checkbox"
                    checked={exportOptions.includeUncertainty}
                    onChange={(e) => handleExportOptionChange('includeUncertainty', e.target.checked)}
                    className="rounded"
                    disabled={selectedFormat === 'csv'}
                  />
                  <span className="text-slate-300">Include uncertainty scores and alternative positions</span>
                </label>
                <label className="flex items-center gap-3">
                  <input
                    type="checkbox"
                    checked={exportOptions.anonymizeUsers}
                    onChange={(e) => handleExportOptionChange('anonymizeUsers', e.target.checked)}
                    className="rounded"
                  />
                  <span className="text-slate-300">Anonymize user identifiers (recommended)</span>
                </label>
              </div>
            </div>

            {/* Task Type Filter */}
            <div>
              <h4 className="font-semibold text-slate-200 mb-3">Task Types</h4>
              <div className="grid grid-cols-2 gap-2">
                <button
                  onClick={() => setExportOptions(prev => ({ 
                    ...prev, 
                    taskTypes: taskTypes ? [...taskTypes] : [] 
                  }))}
                  className="text-sm text-purple-400 hover:text-purple-300 text-left"
                >
                  Select All
                </button>
                <button
                  onClick={() => setExportOptions(prev => ({ ...prev, taskTypes: [] }))}
                  className="text-sm text-slate-400 hover:text-slate-300 text-left"
                >
                  Clear All
                </button>
              </div>
              <div className="grid grid-cols-2 gap-2 mt-2">
                {taskTypes?.map((taskType: string) => (
                  <label key={taskType} className="flex items-center gap-2">
                    <input
                      type="checkbox"
                      checked={exportOptions.taskTypes.includes(taskType)}
                      onChange={() => handleTaskTypeToggle(taskType)}
                      className="rounded text-xs"
                    />
                    <span className="text-slate-300 text-sm">{taskType}</span>
                  </label>
                ))}
              </div>
            </div>

            {/* Quality Filters */}
            <div>
              <h4 className="font-semibold text-slate-200 mb-3">Quality Filters</h4>
              <div className="space-y-3">
                <div>
                  <label className="block text-sm text-slate-300 mb-1">
                    Minimum Authority Score: {exportOptions.minAuthorityScore.toFixed(2)}
                  </label>
                  <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.01"
                    value={exportOptions.minAuthorityScore}
                    onChange={(e) => handleExportOptionChange('minAuthorityScore', parseFloat(e.target.value))}
                    className="w-full"
                  />
                  <div className="flex justify-between text-xs text-slate-500">
                    <span>Any (0.00)</span>
                    <span>Expert (1.00)</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Date Range */}
            <div>
              <h4 className="font-semibold text-slate-200 mb-3">Date Range</h4>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm text-slate-300 mb-1">Start Date</label>
                  <input
                    type="date"
                    value={exportOptions.dateRange.start || ''}
                    onChange={(e) => handleExportOptionChange('dateRange', {
                      ...exportOptions.dateRange,
                      start: e.target.value || null
                    })}
                    className="w-full p-2 bg-slate-900 border border-slate-600 rounded text-slate-200"
                  />
                </div>
                <div>
                  <label className="block text-sm text-slate-300 mb-1">End Date</label>
                  <input
                    type="date"
                    value={exportOptions.dateRange.end || ''}
                    onChange={(e) => handleExportOptionChange('dateRange', {
                      ...exportOptions.dateRange,
                      end: e.target.value || null
                    })}
                    className="w-full p-2 bg-slate-900 border border-slate-600 rounded text-slate-200"
                  />
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Export Summary */}
        <Card className="border-slate-700">
          <CardHeader>
            <CardTitle>📋 Export Summary</CardTitle>
            <p className="text-slate-400">Preview your dataset configuration</p>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Selected Format Info */}
            <div className="p-4 bg-purple-950/20 rounded-lg border border-purple-700">
              <div className="flex items-center gap-3 mb-2">
                <span className="text-2xl">{selectedFormatInfo?.icon}</span>
                <h4 className="font-semibold text-purple-300">{selectedFormatInfo?.name}</h4>
              </div>
              <p className="text-sm text-purple-200 mb-2">{selectedFormatInfo?.description}</p>
              <Badge className="bg-purple-600">.{selectedFormatInfo?.fileExtension}</Badge>
            </div>

            {/* Dataset Preview */}
            {showPreview && datasetMetrics && (
              <div className="space-y-4">
                <div className="grid grid-cols-3 gap-3">
                  <div className="text-center p-3 bg-slate-800/50 rounded">
                    <div className="text-xl font-bold text-blue-400">{datasetMetrics.totalTasks}</div>
                    <div className="text-xs text-slate-400">Tasks</div>
                  </div>
                  <div className="text-center p-3 bg-slate-800/50 rounded">
                    <div className="text-xl font-bold text-green-400">{datasetMetrics.totalFeedback}</div>
                    <div className="text-xs text-slate-400">Evaluations</div>
                  </div>
                  <div className="text-center p-3 bg-slate-800/50 rounded">
                    <div className="text-xl font-bold text-purple-400">{estimatedFileSize}</div>
                    <div className="text-xs text-slate-400">Est. Size</div>
                  </div>
                </div>

                {/* Quality Metrics */}
                <div>
                  <h5 className="font-semibold text-slate-200 mb-2">Quality Metrics</h5>
                  <div className="space-y-2">
                    <div className="flex justify-between">
                      <span className="text-slate-400">Avg. Accuracy</span>
                      <span className="text-blue-400">{datasetMetrics.qualityMetrics.avgAccuracy.toFixed(1)}/10</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-400">Avg. Utility</span>
                      <span className="text-green-400">{datasetMetrics.qualityMetrics.avgUtility.toFixed(1)}/10</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-400">Avg. Transparency</span>
                      <span className="text-yellow-400">{datasetMetrics.qualityMetrics.avgTransparency.toFixed(1)}/10</span>
                    </div>
                  </div>
                </div>

                {/* Task Distribution */}
                <div>
                  <h5 className="font-semibold text-slate-200 mb-2">Task Distribution</h5>
                  <ResponsiveContainer width="100%" height={150}>
                    <BarChart data={datasetMetrics.taskTypeDistribution}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                      <XAxis dataKey="type" stroke="#9CA3AF" fontSize={10} />
                      <YAxis stroke="#9CA3AF" fontSize={10} />
                      <Tooltip 
                        contentStyle={{ 
                          backgroundColor: '#1F2937', 
                          border: '1px solid #374151',
                          borderRadius: '6px'
                        }}
                      />
                      <Bar dataKey="count" fill="#8B5CF6" radius={[2, 2, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            )}

            {/* Action Buttons */}
            <div className="space-y-3 pt-4 border-t border-slate-600">
              <Button
                onClick={() => setShowPreview(!showPreview)}
                variant="outline"
                className="w-full"
                disabled={!canExport || loadingMetrics}
              >
                {loadingMetrics ? (
                  <>⏳ Loading Preview...</>
                ) : showPreview ? (
                  <>👁️ Hide Preview</>
                ) : (
                  <>👁️ Show Preview</>
                )}
              </Button>

              <Button
                onClick={() => exportMutation.mutate(exportOptions)}
                disabled={!canExport || exportMutation.isPending}
                className="w-full bg-purple-600 hover:bg-purple-700"
                size="lg"
              >
                {exportMutation.isPending ? (
                  <>⬇️ Generating Export...</>
                ) : (
                  <>⬇️ Export Dataset</>
                )}
              </Button>
            </div>

            {!canExport && (
              <div className="text-center text-yellow-400 text-sm">
                ⚠️ Please select at least one task type to export
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Sample Data Preview */}
      {showPreview && selectedFormat && (
        <Card className="border-slate-700">
          <CardHeader>
            <CardTitle>👀 Sample Data Preview</CardTitle>
            <p className="text-slate-400">Example of how your data will be formatted</p>
          </CardHeader>
          <CardContent>
            <div className="bg-slate-900 rounded-lg p-4 font-mono text-sm">
              <div className="text-purple-400 mb-2">// {selectedFormatInfo?.name} Format</div>
              {selectedFormat === 'sft' && (
                <pre className="text-slate-300 whitespace-pre-wrap">
{`{
  "messages": [
    {
      "role": "system",
      "content": "You are a legal AI assistant..."
    },
    {
      "role": "user", 
      "content": "What is the statute of limitations for..."
    },
    {
      "role": "assistant",
      "content": "The statute of limitations varies by jurisdiction..."
    }
  ],
  "task_type": "STATUTORY_RULE_QA",
  "authority_score": 0.85,
  "quality_scores": {
    "accuracy": 9,
    "utility": 8,
    "transparency": 9
  }${exportOptions.includeMetadata ? `,
  "metadata": {
    "timestamp": "2024-01-15T10:30:00Z",
    "evaluator_count": 5,
    "consensus_level": 0.92
  }` : ''}
}`}
                </pre>
              )}

              {selectedFormat === 'preference' && (
                <pre className="text-slate-300 whitespace-pre-wrap">
{`{
  "prompt": "What is the statute of limitations for...",
  "chosen": "The statute of limitations varies by jurisdiction...",
  "rejected": "The statute of limitations is always 3 years...",
  "chosen_metadata": {
    "authority_score": 0.85,
    "quality_score": 8.7
  },
  "rejected_metadata": {
    "authority_score": 0.42,
    "quality_score": 5.2
  }
}`}
                </pre>
              )}

              {selectedFormat === 'research' && (
                <pre className="text-slate-300 whitespace-pre-wrap">
{`{
  "task": {
    "id": 123,
    "type": "STATUTORY_RULE_QA",
    "input": {...},
    "ground_truth": {...}
  },
  "evaluations": [
    {
      "evaluator_id": "eval_001",
      "authority_score": 0.85,
      "feedback": {...},
      "reasoning": "...",
      "timestamp": "2024-01-15T10:30:00Z"
    }
  ],
  "aggregation": {
    "consensus_level": 0.92,
    "uncertainty_score": 0.08,
    "alternative_positions": [...]
  }
}`}
                </pre>
              )}

              {selectedFormat === 'csv' && (
                <pre className="text-slate-300 whitespace-pre-wrap">
{`task_id,task_type,input_text,ground_truth,evaluator_authority,accuracy_score,utility_score,transparency_score,consensus_level
123,STATUTORY_RULE_QA,"What is the statute...","{""answer"": ""varies by jurisdiction""}",0.85,9,8,9,0.92
124,QA,"Define contract law","Contract law governs...",0.72,8,7,8,0.88`}
                </pre>
              )}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}