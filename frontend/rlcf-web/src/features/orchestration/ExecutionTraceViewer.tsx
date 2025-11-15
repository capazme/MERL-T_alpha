/**
 * Execution Trace Viewer
 *
 * Detailed visualization of query execution trace through the pipeline.
 * Shows stages, timings, expert opinions, and full JSON trace.
 */

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@components/ui/Card';
import { Badge } from '@components/ui/Badge';
import { useQueryDetails } from '@hooks/useOrchestration';
import { Loader, Clock, CheckCircle, Brain, Database, Code } from 'lucide-react';
import { ExpertOpinionPanel } from './components/ExpertOpinionPanel';
import { SynthesisViewer } from './components/SynthesisViewer';
import { PipelineMetricsCard } from './components/PipelineMetricsCard';

interface ExecutionTraceViewerProps {
  traceId: string;
}

export function ExecutionTraceViewer({ traceId }: ExecutionTraceViewerProps) {
  const { data: queryData, isLoading } = useQueryDetails(traceId);
  const [showRawJson, setShowRawJson] = useState(false);

  if (isLoading) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center py-12">
          <Loader className="w-8 h-8 animate-spin text-blue-500" />
          <span className="ml-3 text-gray-400">Loading execution trace...</span>
        </CardContent>
      </Card>
    );
  }

  if (!queryData) {
    return (
      <Card>
        <CardContent className="py-12 text-center text-gray-400">
          Query not found or trace unavailable.
        </CardContent>
      </Card>
    );
  }

  const trace = queryData.execution_trace;
  const answer = queryData.answer;
  const metadata = queryData.metadata;

  return (
    <div className="space-y-6">
      {/* Query Info Card */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <span>Query: {traceId}</span>
            <Badge variant="secondary">
              <CheckCircle className="w-3 h-3 mr-1" />
              Completed
            </Badge>
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <h3 className="text-sm font-medium text-gray-400 mb-2">Query Text</h3>
            <p className="text-white bg-gray-800 p-4 rounded-lg">{queryData.query}</p>
          </div>

          {answer && (
            <div>
              <h3 className="text-sm font-medium text-gray-400 mb-2">Answer Preview</h3>
              <div className="bg-gray-800 p-4 rounded-lg space-y-2">
                <p className="text-white line-clamp-3">{answer.primary_answer}</p>
                <div className="flex items-center gap-4 text-sm">
                  <span className="text-gray-400">
                    Confidence: <span className="text-green-400 font-medium">{(answer.confidence * 100).toFixed(1)}%</span>
                  </span>
                  {answer.uncertainty_preserved && (
                    <Badge variant="outline">Uncertainty Preserved</Badge>
                  )}
                </div>
                <p className="text-xs text-gray-500 italic">See detailed synthesis below</p>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Execution Trace */}
      {trace && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Clock className="w-5 h-5" />
              Execution Trace
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Timeline */}
            <div className="space-y-3">
              <h3 className="text-sm font-medium text-gray-400">Pipeline Stages</h3>
              <div className="space-y-2">
                {trace.stages_executed?.map((stage, idx) => (
                  <div key={idx} className="flex items-center gap-3 p-3 bg-gray-800 rounded-lg">
                    <div className="w-8 h-8 rounded-full bg-blue-500/20 flex items-center justify-center text-blue-400 font-medium">
                      {idx + 1}
                    </div>
                    <div className="flex-1">
                      <div className="text-white font-medium capitalize">{stage.replace('_', ' ')}</div>
                      {trace.stage_timings?.[stage] && (
                        <div className="text-sm text-gray-400">
                          {trace.stage_timings[stage].toFixed(0)}ms
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Agents Used */}
            {trace.agents_used && trace.agents_used.length > 0 && (
              <div className="space-y-3">
                <h3 className="text-sm font-medium text-gray-400 flex items-center gap-2">
                  <Database className="w-4 h-4" />
                  Retrieval Agents Used
                </h3>
                <div className="flex flex-wrap gap-2">
                  {trace.agents_used.map((agent, idx) => (
                    <Badge key={idx} variant="outline">
                      {agent.replace('_agent', '')}
                    </Badge>
                  ))}
                </div>
              </div>
            )}

            {/* Quick Metrics Overview */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <MetricCard label="Total Time" value={`${trace.total_time_ms?.toFixed(0)}ms`} />
              <MetricCard label="Iterations" value={trace.iterations?.toString() || '1'} />
              <MetricCard label="Tokens Used" value={trace.tokens_used?.toLocaleString() || 'N/A'} />
              <MetricCard label="Errors" value={trace.errors?.length?.toString() || '0'} />
            </div>
            <p className="text-xs text-gray-500 italic text-center">See detailed performance metrics below</p>

            {/* Errors */}
            {trace.errors && trace.errors.length > 0 && (
              <div className="space-y-2">
                <h3 className="text-sm font-medium text-red-400">Errors</h3>
                {trace.errors.map((error, idx) => (
                  <div key={idx} className="p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-red-300 text-sm">
                    {error}
                  </div>
                ))}
              </div>
            )}

            {/* Raw JSON Toggle */}
            <div className="pt-4 border-t border-gray-700">
              <button
                onClick={() => setShowRawJson(!showRawJson)}
                className="flex items-center gap-2 text-sm text-blue-400 hover:text-blue-300 transition-colors"
              >
                <Code className="w-4 h-4" />
                {showRawJson ? 'Hide' : 'Show'} Raw JSON
              </button>

              {showRawJson && (
                <pre className="mt-4 p-4 bg-black rounded-lg overflow-x-auto text-xs text-gray-300">
                  {JSON.stringify(trace, null, 2)}
                </pre>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Metadata */}
      {metadata && (
        <Card>
          <CardHeader>
            <CardTitle>Query Metadata</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              {metadata.intent_detected && (
                <MetricCard label="Intent" value={metadata.intent_detected} />
              )}
              {metadata.complexity_score && (
                <MetricCard label="Complexity" value={(metadata.complexity_score * 100).toFixed(0) + '%'} />
              )}
              {metadata.concepts_identified && (
                <div className="space-y-2">
                  <h4 className="text-sm font-medium text-gray-400">Concepts</h4>
                  <div className="flex flex-wrap gap-1">
                    {metadata.concepts_identified.slice(0, 5).map((concept: string, idx: number) => (
                      <Badge key={idx} variant="outline" size="sm">
                        {concept}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Performance Metrics Card */}
      {trace?.stage_timings && (
        <PipelineMetricsCard
          stageTimings={trace.stage_timings}
          totalTimeMs={trace.total_time_ms}
        />
      )}

      {/* Synthesis Viewer */}
      {answer && <SynthesisViewer answer={answer} />}

      {/* Expert Opinion Panel */}
      {trace?.experts_consulted && (
        <ExpertOpinionPanel
          experts={trace.experts_consulted}
          opinions={trace.expert_opinions}
        />
      )}
    </div>
  );
}

function MetricCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-gray-800 p-4 rounded-lg">
      <div className="text-sm text-gray-400 mb-1">{label}</div>
      <div className="text-xl font-semibold text-white">{value}</div>
    </div>
  );
}
