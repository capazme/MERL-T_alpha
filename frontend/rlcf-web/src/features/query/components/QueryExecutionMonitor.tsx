/**
 * Query Execution Monitor Component
 *
 * Real-time monitoring of query execution progress through the MERL-T pipeline.
 * Shows current stage, progress bar, stage timeline, and live logs.
 */

import { usePollQueryStatus } from '@/hooks/useOrchestration';
import { Card, CardHeader, CardTitle, CardContent } from '@components/ui/Card';
import { AnimatedProgressBar } from '@components/ui/Progress';
import {
  Loader,
  CheckCircle2,
  Circle,
  XCircle,
  FileSearch,
  Route,
  Database,
  Users,
  Sparkles,
  RefreshCw,
  AlertCircle,
  ChevronDown,
  ChevronRight,
  MessageSquare,
  ThumbsUp,
  ThumbsDown
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useState } from 'react';

interface QueryExecutionMonitorProps {
  /** Trace ID of the query being executed */
  traceId: string;
}

/**
 * Pipeline stages with metadata
 */
const PIPELINE_STAGES = [
  { key: 'preprocessing', label: 'Preprocessing', icon: FileSearch, description: 'Query understanding e NER' },
  { key: 'router', label: 'Router', icon: Route, description: 'Piano di esecuzione LLM' },
  { key: 'retrieval', label: 'Retrieval', icon: Database, description: 'KG, API, VectorDB' },
  { key: 'experts', label: 'Experts', icon: Users, description: '4 esperti legali AI' },
  { key: 'synthesis', label: 'Synthesis', icon: Sparkles, description: 'Sintesi opinioni' },
  { key: 'iteration', label: 'Iteration', icon: RefreshCw, description: 'Controllo qualità' },
  { key: 'refinement', label: 'Refinement', icon: CheckCircle2, description: 'Raffinamento finale' },
] as const;

/**
 * Get stage status based on current progress
 */
function getStageStatus(
  stageKey: string,
  currentStage: string | null | undefined,
  progressPercent: number | null | undefined
): 'completed' | 'in-progress' | 'pending' | 'error' {
  if (!currentStage || progressPercent === null || progressPercent === undefined) {
    return 'pending';
  }

  // Find stage indices
  const stageIndex = PIPELINE_STAGES.findIndex((s) => s.key === stageKey);
  const currentIndex = PIPELINE_STAGES.findIndex((s) => s.key === currentStage);

  if (currentIndex === -1) return 'pending';

  if (stageIndex < currentIndex) return 'completed';
  if (stageIndex === currentIndex) return 'in-progress';
  return 'pending';
}

/**
 * Stage item component with expandable details
 */
function StageItem({
  stage,
  status,
  stageResults,
}: {
  stage: typeof PIPELINE_STAGES[number];
  status: 'completed' | 'in-progress' | 'pending' | 'error';
  stageResults?: any;
}) {
  const [isExpanded, setIsExpanded] = useState(false);
  const Icon = stage.icon;

  const statusConfig = {
    completed: {
      icon: CheckCircle2,
      iconColor: 'text-green-400',
      bgColor: 'bg-green-500/10',
      borderColor: 'border-green-500/30',
    },
    'in-progress': {
      icon: Loader,
      iconColor: 'text-blue-400 animate-spin',
      bgColor: 'bg-blue-500/10',
      borderColor: 'border-blue-500/30',
    },
    pending: {
      icon: Circle,
      iconColor: 'text-gray-600',
      bgColor: 'bg-gray-800/50',
      borderColor: 'border-gray-700',
    },
    error: {
      icon: XCircle,
      iconColor: 'text-red-400',
      bgColor: 'bg-red-500/10',
      borderColor: 'border-red-500/30',
    },
  };

  const config = statusConfig[status];
  const StatusIcon = config.icon;
  const hasResults = stageResults && Object.keys(stageResults).length > 0;
  const canExpand = hasResults && status === 'completed';

  return (
    <motion.div
      initial={{ opacity: 0, x: -10 }}
      animate={{ opacity: 1, x: 0 }}
      className={`rounded-lg border ${config.bgColor} ${config.borderColor} transition-all`}
    >
      {/* Stage Header */}
      <div
        className={`flex items-center gap-3 p-3 ${canExpand ? 'cursor-pointer hover:bg-white/5' : ''}`}
        onClick={() => canExpand && setIsExpanded(!isExpanded)}
      >
        {/* Status Icon */}
        <StatusIcon className={`w-5 h-5 flex-shrink-0 ${config.iconColor}`} />

        {/* Stage Info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <Icon className="w-4 h-4 text-gray-400 flex-shrink-0" />
            <span className="text-sm font-medium text-white">{stage.label}</span>
          </div>
          <p className="text-xs text-gray-500 mt-0.5">{stage.description}</p>
        </div>

        {/* Expand Icon */}
        {canExpand && (
          <div className="flex-shrink-0">
            {isExpanded ? (
              <ChevronDown className="w-4 h-4 text-gray-400" />
            ) : (
              <ChevronRight className="w-4 h-4 text-gray-400" />
            )}
          </div>
        )}
      </div>

      {/* Stage Details (Expandable) */}
      <AnimatePresence>
        {isExpanded && hasResults && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="overflow-hidden"
          >
            <div className="px-3 pb-3 pt-2 border-t border-gray-700/50">
              <StageDetails stageKey={stage.key} results={stageResults} />
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}

/**
 * Stage details renderer
 */
function StageDetails({ stageKey, results }: { stageKey: string; results: any }) {
  if (!results) return null;

  switch (stageKey) {
    case 'preprocessing':
      return <PreprocessingDetails data={results} />;
    case 'router':
      return <RouterDetails data={results} />;
    case 'retrieval':
      return <RetrievalDetails data={results} />;
    case 'experts':
      return <ExpertsDetails data={results} />;
    case 'synthesis':
      return <SynthesisDetails data={results} />;
    default:
      return <pre className="text-xs text-gray-400">{JSON.stringify(results, null, 2)}</pre>;
  }
}

/**
 * Preprocessing details component
 */
function PreprocessingDetails({ data }: { data: any }) {
  return (
    <div className="space-y-2 text-sm">
      <div className="grid grid-cols-2 gap-2">
        <div>
          <span className="text-gray-500">Intent:</span>{' '}
          <span className="text-blue-400 font-medium">{data.intent}</span>
        </div>
        <div>
          <span className="text-gray-500">Confidence:</span>{' '}
          <span className="text-green-400 font-medium">{(data.confidence * 100).toFixed(0)}%</span>
        </div>
      </div>
      <div className="grid grid-cols-2 gap-2">
        <div>
          <span className="text-gray-500">Entities:</span>{' '}
          <span className="text-gray-300">{data.entities_count}</span>
        </div>
        <div>
          <span className="text-gray-500">Enrichment sources:</span>{' '}
          <span className="text-gray-300">{data.enrichment_sources}</span>
        </div>
      </div>
      {data.legal_concepts && data.legal_concepts.length > 0 && (
        <div>
          <span className="text-gray-500">Concetti:</span>{' '}
          <div className="flex flex-wrap gap-1 mt-1">
            {data.legal_concepts.map((concept: string, i: number) => (
              <span
                key={i}
                className="px-2 py-0.5 bg-blue-500/20 text-blue-300 rounded text-xs"
              >
                {concept}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

/**
 * Router details component
 */
function RouterDetails({ data }: { data: any }) {
  return (
    <div className="space-y-2 text-sm">
      <div>
        <span className="text-gray-500">Agents selezionati:</span>
        <div className="flex flex-wrap gap-1 mt-1">
          {Object.entries(data.agents_selected || {}).map(([agent, enabled]: [string, any]) =>
            enabled ? (
              <span
                key={agent}
                className="px-2 py-0.5 bg-green-500/20 text-green-300 rounded text-xs"
              >
                {agent}
              </span>
            ) : null
          )}
        </div>
      </div>
      <div>
        <span className="text-gray-500">Experts selezionati:</span>
        <div className="flex flex-wrap gap-1 mt-1">
          {(data.experts_selected || []).map((expert: string, i: number) => (
            <span
              key={i}
              className="px-2 py-0.5 bg-purple-500/20 text-purple-300 rounded text-xs"
            >
              {expert}
            </span>
          ))}
        </div>
      </div>
      <div className="grid grid-cols-2 gap-2">
        <div>
          <span className="text-gray-500">Synthesis mode:</span>{' '}
          <span className="text-gray-300">{data.synthesis_mode}</span>
        </div>
        <div>
          <span className="text-gray-500">Confidence threshold:</span>{' '}
          <span className="text-gray-300">{data.confidence_threshold}</span>
        </div>
      </div>
    </div>
  );
}

/**
 * Retrieval details component
 */
function RetrievalDetails({ data }: { data: any }) {
  return (
    <div className="space-y-2 text-sm">
      {Object.entries(data || {}).map(([agent, info]: [string, any]) => (
        <div key={agent} className="flex items-center justify-between">
          <span className="text-gray-400">{agent}:</span>
          <div className="flex items-center gap-2">
            <span className="text-gray-300">{info.count} risultati</span>
            {info.success ? (
              <CheckCircle2 className="w-4 h-4 text-green-400" />
            ) : (
              <XCircle className="w-4 h-4 text-red-400" />
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

/**
 * Experts details component
 */
function ExpertsDetails({ data }: { data: any[] }) {
  return (
    <div className="space-y-3">
      {data.map((expert, index) => (
        <div
          key={index}
          className="p-3 bg-gray-800/50 border border-gray-700 rounded"
        >
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-white">
              {expert.expert_type}
            </span>
            <span className="text-xs text-green-400">
              {(expert.confidence * 100).toFixed(0)}% confidence
            </span>
          </div>
          <p className="text-xs text-gray-400 leading-relaxed">
            {expert.interpretation_preview}
          </p>
          <div className="flex gap-2 mt-2">
            <button className="p-1 hover:bg-green-500/20 rounded transition-colors">
              <ThumbsUp className="w-3 h-3 text-gray-500 hover:text-green-400" />
            </button>
            <button className="p-1 hover:bg-red-500/20 rounded transition-colors">
              <ThumbsDown className="w-3 h-3 text-gray-500 hover:text-red-400" />
            </button>
            <button className="p-1 hover:bg-blue-500/20 rounded transition-colors">
              <MessageSquare className="w-3 h-3 text-gray-500 hover:text-blue-400" />
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}

/**
 * Synthesis details component
 */
function SynthesisDetails({ data }: { data: any }) {
  return (
    <div className="space-y-3 text-sm">
      <div className="grid grid-cols-2 gap-2">
        <div>
          <span className="text-gray-500">Confidence:</span>{' '}
          <span className="text-green-400 font-medium">
            {(data.confidence * 100).toFixed(0)}%
          </span>
        </div>
        <div>
          <span className="text-gray-500">Consensus:</span>{' '}
          <span className="text-blue-400 font-medium">
            {(data.consensus_level * 100).toFixed(0)}%
          </span>
        </div>
      </div>
      <div>
        <span className="text-gray-500">Answer preview:</span>
        <p className="text-gray-300 text-xs mt-1 leading-relaxed bg-gray-800/50 p-2 rounded">
          {data.answer_preview}
        </p>
      </div>
      <div className="flex gap-2">
        <button className="px-3 py-1.5 bg-green-500/20 hover:bg-green-500/30 text-green-300 rounded text-xs transition-colors flex items-center gap-1">
          <ThumbsUp className="w-3 h-3" />
          Approva
        </button>
        <button className="px-3 py-1.5 bg-red-500/20 hover:bg-red-500/30 text-red-300 rounded text-xs transition-colors flex items-center gap-1">
          <ThumbsDown className="w-3 h-3" />
          Rifiuta
        </button>
        <button className="px-3 py-1.5 bg-blue-500/20 hover:bg-blue-500/30 text-blue-300 rounded text-xs transition-colors flex items-center gap-1">
          <MessageSquare className="w-3 h-3" />
          Feedback
        </button>
      </div>
    </div>
  );
}

/**
 * Query Execution Monitor
 */
export function QueryExecutionMonitor({ traceId }: QueryExecutionMonitorProps) {
  const status = usePollQueryStatus(traceId);

  // Handle loading state
  if (!status) {
    return (
      <Card>
        <CardContent className="p-8">
          <div className="flex flex-col items-center justify-center gap-4">
            <Loader className="w-8 h-8 text-blue-400 animate-spin" />
            <p className="text-sm text-gray-400">Connessione al sistema...</p>
          </div>
        </CardContent>
      </Card>
    );
  }

  const {
    status: queryStatus,
    current_stage,
    progress_percent,
    stage_logs,
    stage_results,
    error,
  } = status;

  const progressValue = progress_percent ?? 0;
  const isProcessing = queryStatus === 'pending' || queryStatus === 'processing';
  const hasError = queryStatus === 'failed' || !!error;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          {isProcessing ? (
            <>
              <Loader className="w-5 h-5 text-blue-400 animate-spin" />
              Query in elaborazione...
            </>
          ) : hasError ? (
            <>
              <AlertCircle className="w-5 h-5 text-red-400" />
              Errore durante l'esecuzione
            </>
          ) : (
            <>
              <CheckCircle2 className="w-5 h-5 text-green-400" />
              Esecuzione completata
            </>
          )}
        </CardTitle>
        <p className="text-sm text-gray-400 mt-1">
          Traccia ID: <span className="font-mono text-gray-300">{traceId}</span>
        </p>
      </CardHeader>

      <CardContent className="space-y-6">
        {/* Progress Bar */}
        <div>
          <AnimatedProgressBar
            value={progressValue}
            max={100}
            label={`Progresso (${PIPELINE_STAGES.findIndex((s) => s.key === current_stage) + 1}/7 fasi)`}
            colorScheme="gradient"
          />
        </div>

        {/* Error Message */}
        {hasError && error && (
          <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-4">
            <div className="flex items-start gap-3">
              <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
              <div>
                <h4 className="text-sm font-semibold text-red-300 mb-1">
                  Errore di esecuzione
                </h4>
                <p className="text-sm text-red-200">{error}</p>
              </div>
            </div>
          </div>
        )}

        {/* Pipeline Stages */}
        <div>
          <h3 className="text-sm font-semibold text-gray-300 mb-3">
            Fasi della Pipeline
          </h3>
          <div className="space-y-2">
            {PIPELINE_STAGES.map((stage) => {
              const stageStatus = getStageStatus(stage.key, current_stage, progress_percent);
              const stageData = stage_results?.[stage.key];
              return (
                <StageItem
                  key={stage.key}
                  stage={stage}
                  status={stageStatus}
                  stageResults={stageData}
                />
              );
            })}
          </div>
        </div>

        {/* Stage Logs */}
        {stage_logs && stage_logs.length > 0 && (
          <div>
            <h3 className="text-sm font-semibold text-gray-300 mb-3">
              Log di Esecuzione
            </h3>
            <div className="bg-gray-900 border border-gray-700 rounded-lg p-4 max-h-64 overflow-y-auto">
              <div className="space-y-1 font-mono text-xs">
                <AnimatePresence>
                  {stage_logs.map((log: string, index: number) => (
                    <motion.div
                      key={index}
                      initial={{ opacity: 0, y: -5 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0 }}
                      transition={{ delay: index * 0.05 }}
                      className="text-gray-400"
                    >
                      {log}
                    </motion.div>
                  ))}
                </AnimatePresence>
              </div>
            </div>
          </div>
        )}

        {/* Current Status Info */}
        <div className="pt-4 border-t border-gray-700">
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <span className="text-gray-500">Stato:</span>{' '}
              <span
                className={
                  queryStatus === 'completed'
                    ? 'text-green-400 font-medium'
                    : queryStatus === 'failed'
                    ? 'text-red-400 font-medium'
                    : 'text-blue-400 font-medium'
                }
              >
                {queryStatus === 'pending'
                  ? 'In attesa'
                  : queryStatus === 'processing'
                  ? 'In elaborazione'
                  : queryStatus === 'completed'
                  ? 'Completata'
                  : 'Fallita'}
              </span>
            </div>
            <div>
              <span className="text-gray-500">Fase corrente:</span>{' '}
              <span className="text-gray-300 font-medium">
                {current_stage
                  ? PIPELINE_STAGES.find((s) => s.key === current_stage)?.label || current_stage
                  : 'N/A'}
              </span>
            </div>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
