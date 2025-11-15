/**
 * Query Submission Page
 *
 * Main page for submitting legal queries to the MERL-T orchestration layer.
 * Integrates QueryForm, QueryContextPanel, QueryOptionsPanel, and RecentQueriesPanel.
 */

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, Sparkles, ArrowRight } from 'lucide-react';
import { useExecuteQuery } from '@/hooks/useOrchestration';
import { useQueryStore } from '@/app/store/query';
import { useAuthStore } from '@/app/store/auth';
import { QueryForm } from './components/QueryForm';
import { QueryContextPanel } from './components/QueryContextPanel';
import { QueryOptionsPanel } from './components/QueryOptionsPanel';
import { RecentQueriesPanel } from './components/RecentQueriesPanel';
import { QueryExecutionMonitor } from './components/QueryExecutionMonitor';
import { Button } from '@components/ui/Button';
import type { QueryFormData } from './validation';
import type { QueryRequest } from '@/types/orchestration';

export function QuerySubmission() {
  const navigate = useNavigate();
  const { user } = useAuthStore();
  const { queryContext, queryOptions, setCurrentTraceId } = useQueryStore();
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [executingTraceId, setExecutingTraceId] = useState<string | null>(null);

  const { mutate: executeQuery, isPending } = useExecuteQuery();

  const handleQuerySubmit = async (data: QueryFormData) => {
    setErrorMessage(null);

    // Build query request
    const queryRequest: QueryRequest = {
      query: data.query,
      context: {
        ...queryContext,
        // Add user_id to context if available (not in QueryContext type but might be used)
      },
      options: queryOptions,
    };

    // Execute query via TanStack Query mutation
    executeQuery(queryRequest, {
      onSuccess: (response) => {
        console.log('[QuerySubmission] Query executed successfully, response:', response);
        console.log('[QuerySubmission] trace_id:', response.trace_id);

        // Save trace ID to store
        setCurrentTraceId(response.trace_id);

        // Show execution monitor instead of navigating immediately
        setExecutingTraceId(response.trace_id);
        console.log('[QuerySubmission] executingTraceId set to:', response.trace_id);

        // Scroll to monitor
        window.scrollTo({ top: 0, behavior: 'smooth' });
      },
      onError: (error: any) => {
        console.error('[QuerySubmission] Query execution failed:', error);

        // Extract error message
        const message =
          error?.response?.data?.detail ||
          error?.message ||
          'Si è verificato un errore durante l\'esecuzione della query. Riprova.';

        setErrorMessage(message);

        // Scroll to top to show error
        window.scrollTo({ top: 0, behavior: 'smooth' });
      },
    });
  };

  const handleViewResults = () => {
    if (executingTraceId) {
      navigate(`/query/results/${executingTraceId}`);
    }
  };

  const handleNewQuery = () => {
    setExecutingTraceId(null);
    setErrorMessage(null);
  };

  // Debug logging
  console.log('[QuerySubmission] Render - executingTraceId:', executingTraceId);
  console.log('[QuerySubmission] Render - isPending:', isPending);
  console.log('[QuerySubmission] Render - errorMessage:', errorMessage);

  return (
    <div className="min-h-screen bg-gray-950 py-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <div className="mb-8">
          <div className="flex items-center gap-3 mb-3">
            <div className="p-2 bg-blue-500/10 rounded-lg">
              <Search className="w-8 h-8 text-blue-400" />
            </div>
            <div>
              <h1 className="text-3xl font-bold text-white">
                Interroga MERL-T
              </h1>
              <p className="text-gray-400 mt-1">
                Sistema Multi-Expert per Ricerca e Analisi Legale
              </p>
            </div>
          </div>

          {/* Info Banner */}
          <div className="bg-gradient-to-r from-blue-500/10 to-purple-500/10 border border-blue-500/20 rounded-lg p-4">
            <div className="flex items-start gap-3">
              <Sparkles className="w-5 h-5 text-blue-400 mt-0.5 flex-shrink-0" />
              <div className="flex-1">
                <h3 className="text-sm font-semibold text-white mb-1">
                  Come funziona MERL-T
                </h3>
                <p className="text-sm text-gray-300 leading-relaxed">
                  Il sistema analizza la tua query attraverso <strong>4 esperti AI</strong>
                  {' '}(Interpretazione Letterale, Sistematico-Teleologica, Bilanciamento
                  Principi, Analisi Precedenti) che consultano{' '}
                  <strong>normativa, giurisprudenza e dottrina</strong>. Le risposte
                  vengono sintetizzate preservando eventuali divergenze interpretative
                  (principio RLCF).
                </p>
              </div>
            </div>
          </div>
        </div>

        {/* Conditional Rendering: Show Monitor if query is executing, else show Form */}
        {isPending || executingTraceId ? (
          <div className="space-y-6">
            {/* Execution Monitor - show loading state if no trace_id yet */}
            {executingTraceId ? (
              <QueryExecutionMonitor traceId={executingTraceId} />
            ) : (
              <div className="bg-gray-900 border border-gray-800 rounded-lg p-8">
                <div className="flex flex-col items-center justify-center space-y-4">
                  <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500"></div>
                  <p className="text-gray-400">Inizializzazione query in corso...</p>
                  <p className="text-sm text-gray-600">Il monitor dettagliato apparirà a breve</p>
                </div>
              </div>
            )}

            {/* Action Buttons */}
            <div className="flex items-center justify-center gap-4">
              <Button onClick={handleNewQuery} variant="outline">
                Nuova Query
              </Button>
              <Button onClick={handleViewResults} className="gap-2">
                Vedi Risultati Completi
                <ArrowRight className="w-4 h-4" />
              </Button>
            </div>
          </div>
        ) : (
          /* Main Layout: Form (left) + Recent Queries (right) */
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Left Column: Form + Context + Options (2/3 width) */}
            <div className="lg:col-span-2 space-y-6">
              {/* Query Form */}
              <QueryForm
                onSubmit={handleQuerySubmit}
                isSubmitting={isPending}
                error={errorMessage}
              />

              {/* Context Configuration */}
              <QueryContextPanel defaultOpen={false} />

              {/* Execution Options */}
              <QueryOptionsPanel defaultOpen={false} />
            </div>

            {/* Right Column: Recent Queries Sidebar (1/3 width) */}
            <div className="lg:col-span-1">
              <div className="sticky top-6">
                <RecentQueriesPanel />
              </div>
            </div>
          </div>
        )}

        {/* Bottom Info */}
        <div className="mt-8 text-center">
          <p className="text-xs text-gray-600">
            Powered by MERL-T (Multi-Expert Legal Retrieval Transformer) | RLCF Framework
            v1.0
          </p>
          <p className="text-xs text-gray-700 mt-1">
            {user ? (
              <>
                Logged in as <span className="text-gray-500">{user.username}</span>
              </>
            ) : (
              'Not authenticated'
            )}
          </p>
        </div>
      </div>
    </div>
  );
}
