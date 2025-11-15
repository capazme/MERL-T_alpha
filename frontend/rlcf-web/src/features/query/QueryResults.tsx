/**
 * Query Results Page
 *
 * Displays legal query results with answer, provenance, and feedback options.
 * Uses tabbed interface: Answer | Provenance | Feedback
 */

import { useParams, useNavigate } from 'react-router-dom';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@components/ui/Tabs';
import { Badge } from '@components/ui/Badge';
import { Button } from '@components/ui/Button';
import { Card, CardContent } from '@components/ui/Card';
import { useQueryDetails } from '@hooks/useOrchestration';
import { ExecutionTraceViewer } from '@features/orchestration/ExecutionTraceViewer';
import { AnswerDisplay } from './components/AnswerDisplay';
import { LegalBasisPanel } from './components/LegalBasisPanel';
import { JurisprudencePanel } from './components/JurisprudencePanel';
import { AlternativeInterpretationsPanel } from './components/AlternativeInterpretationsPanel';
import {
  FileText,
  ArrowLeft,
  Loader,
  AlertCircle,
  CheckCircle,
  Clock,
  XCircle,
  MessageSquare,
} from 'lucide-react';
import type { QueryStatus } from '@/types/orchestration';

const STATUS_CONFIG: Record<
  QueryStatus,
  { icon: React.ReactNode; color: string; label: string }
> = {
  pending: {
    icon: <Clock className="w-4 h-4" />,
    color: 'bg-yellow-500/20 border-yellow-500/40 text-yellow-300',
    label: 'In Attesa',
  },
  processing: {
    icon: <Loader className="w-4 h-4 animate-spin" />,
    color: 'bg-blue-500/20 border-blue-500/40 text-blue-300',
    label: 'Elaborazione',
  },
  completed: {
    icon: <CheckCircle className="w-4 h-4" />,
    color: 'bg-green-500/20 border-green-500/40 text-green-300',
    label: 'Completata',
  },
  failed: {
    icon: <XCircle className="w-4 h-4" />,
    color: 'bg-red-500/20 border-red-500/40 text-red-300',
    label: 'Fallita',
  },
};

export function QueryResults() {
  const { traceId } = useParams<{ traceId: string }>();
  const navigate = useNavigate();

  const { data: queryData, isLoading, error } = useQueryDetails(traceId || '');

  const statusConfig = queryData ? STATUS_CONFIG[queryData.status as QueryStatus] : STATUS_CONFIG.pending;

  // Loading State
  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-950 py-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <Card>
            <CardContent className="flex flex-col items-center justify-center py-24">
              <Loader className="w-12 h-12 animate-spin text-blue-500 mb-4" />
              <p className="text-lg text-gray-400">Caricamento risultati query...</p>
              <p className="text-sm text-gray-600 mt-2">Trace ID: {traceId}</p>
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  // Error State
  if (error || !queryData) {
    return (
      <div className="min-h-screen bg-gray-950 py-8">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <Card className="border-red-500/30">
            <CardContent className="flex flex-col items-center justify-center py-24">
              <AlertCircle className="w-12 h-12 text-red-400 mb-4" />
              <h2 className="text-xl font-semibold text-white mb-2">Query non trovata</h2>
              <p className="text-gray-400 text-center max-w-md mb-6">
                {error
                  ? `Errore: ${(error as any)?.message || 'Impossibile caricare i risultati'}`
                  : `La query con Trace ID "${traceId}" non è stata trovata o non è disponibile.`}
              </p>
              <Button onClick={() => navigate('/query')} variant="default">
                <ArrowLeft className="w-4 h-4 mr-2" />
                Torna alla ricerca
              </Button>
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  const hasAnswer = queryData.answer !== null && queryData.answer !== undefined;
  const hasTrace = queryData.execution_trace !== null && queryData.execution_trace !== undefined;

  return (
    <div className="min-h-screen bg-gray-950 py-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center gap-4 mb-4">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => navigate('/query')}
              className="flex items-center gap-2"
            >
              <ArrowLeft className="w-4 h-4" />
              Nuova Query
            </Button>

            <div className="flex-1" />

            {/* Status Badge */}
            <Badge variant="outline" className={statusConfig.color}>
              {statusConfig.icon}
              <span className="ml-1.5">{statusConfig.label}</span>
            </Badge>
          </div>

          <div className="flex items-start gap-4">
            <div className="p-3 bg-green-500/10 rounded-lg">
              <FileText className="w-8 h-8 text-green-400" />
            </div>

            <div className="flex-1">
              <h1 className="text-3xl font-bold text-white mb-2">Risultati Query</h1>

              {/* Query Text */}
              <div className="bg-gray-800/50 border border-gray-700 rounded-lg p-4 mb-3">
                <p className="text-sm text-gray-400 mb-2 font-medium">Domanda Originale:</p>
                <p className="text-white leading-relaxed">{queryData.query}</p>
              </div>

              {/* Trace ID */}
              <div className="flex items-center gap-4 text-sm text-gray-500">
                <span>
                  Trace ID: <code className="text-blue-400 font-mono">{traceId}</code>
                </span>
                {queryData.timestamp && (
                  <>
                    <span>•</span>
                    <span>
                      Eseguita il:{' '}
                      {new Date(queryData.timestamp).toLocaleString('it-IT', {
                        dateStyle: 'medium',
                        timeStyle: 'short',
                      })}
                    </span>
                  </>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* Main Content - Tabs */}
        <Tabs defaultValue="answer" className="space-y-6">
          <TabsList className="bg-gray-900 p-1 rounded-lg inline-flex gap-1">
            <TabsTrigger value="answer" className="flex items-center gap-2">
              <FileText className="w-4 h-4" />
              Risposta
            </TabsTrigger>
            <TabsTrigger value="provenance" className="flex items-center gap-2">
              <Clock className="w-4 h-4" />
              Provenienza
            </TabsTrigger>
            <TabsTrigger value="feedback" className="flex items-center gap-2">
              <MessageSquare className="w-4 h-4" />
              Feedback
            </TabsTrigger>
          </TabsList>

          {/* Tab 1: Answer */}
          <TabsContent value="answer">
            <div className="space-y-6">
              {/* Answer Display */}
              {hasAnswer ? (
                <>
                  <AnswerDisplay answer={queryData.answer} />

                  {/* Legal Basis */}
                  {queryData.answer.legal_basis && queryData.answer.legal_basis.length > 0 && (
                    <LegalBasisPanel legalBasis={queryData.answer.legal_basis} />
                  )}

                  {/* Jurisprudence */}
                  {queryData.answer.jurisprudence && queryData.answer.jurisprudence.length > 0 && (
                    <JurisprudencePanel jurisprudence={queryData.answer.jurisprudence} />
                  )}

                  {/* Alternative Interpretations */}
                  {queryData.answer.alternative_interpretations &&
                    queryData.answer.alternative_interpretations.length > 0 && (
                      <AlternativeInterpretationsPanel
                        interpretations={queryData.answer.alternative_interpretations}
                      />
                    )}
                </>
              ) : (
                <Card>
                  <CardContent className="py-12 text-center">
                    <AlertCircle className="w-12 h-12 text-yellow-400 mx-auto mb-4" />
                    <h3 className="text-lg font-semibold text-white mb-2">
                      Risposta non disponibile
                    </h3>
                    <p className="text-gray-400 max-w-md mx-auto">
                      {queryData.status === 'processing'
                        ? 'La query è ancora in elaborazione. Ricarica la pagina tra qualche istante.'
                        : queryData.status === 'failed'
                          ? 'La query è fallita durante l\'elaborazione. Controlla la traccia di esecuzione per dettagli sugli errori.'
                          : 'La risposta non è ancora disponibile per questa query.'}
                    </p>
                  </CardContent>
                </Card>
              )}
            </div>
          </TabsContent>

          {/* Tab 2: Provenance (Execution Trace) */}
          <TabsContent value="provenance">
            {hasTrace ? (
              <ExecutionTraceViewer traceId={traceId || ''} />
            ) : (
              <Card>
                <CardContent className="py-12 text-center">
                  <AlertCircle className="w-12 h-12 text-yellow-400 mx-auto mb-4" />
                  <h3 className="text-lg font-semibold text-white mb-2">
                    Traccia di esecuzione non disponibile
                  </h3>
                  <p className="text-gray-400 max-w-md mx-auto">
                    La traccia di esecuzione non è stata generata per questa query. Potrebbe
                    essere stata disabilitata nelle opzioni di esecuzione.
                  </p>
                </CardContent>
              </Card>
            )}
          </TabsContent>

          {/* Tab 3: Feedback (Placeholder for Phase 4) */}
          <TabsContent value="feedback">
            <Card>
              <CardContent className="py-12 text-center">
                <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-purple-500/20 mb-4">
                  <MessageSquare className="w-8 h-8 text-purple-400" />
                </div>
                <h3 className="text-xl font-semibold text-white mb-2">Feedback Interface</h3>
                <p className="text-gray-400 max-w-md mx-auto">
                  L'interfaccia di feedback (User Feedback, RLCF Expert Feedback, NER Corrections)
                  sarà implementata nella Fase 4.
                </p>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
