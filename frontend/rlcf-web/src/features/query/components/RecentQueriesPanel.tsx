/**
 * Recent Queries Panel Component
 *
 * Displays a list of recent queries with quick access to reload them.
 * Shows query text, timestamp, status, and confidence score.
 */

import { Card, CardHeader, CardTitle, CardContent } from '@components/ui/Card';
import { Badge } from '@components/ui/Badge';
import { Clock, CheckCircle, XCircle, Loader, AlertCircle } from 'lucide-react';
import { useQueryHistory } from '@/hooks/useOrchestration';
import { useQueryStore } from '@/app/store/query';
import { useAuthStore } from '@/app/store/auth';
import type { QueryStatus } from '@/types/orchestration';
import { formatDistanceToNow } from 'date-fns';
import { it } from 'date-fns/locale';

const STATUS_CONFIG: Record<
  QueryStatus,
  { icon: React.ReactNode; color: string; label: string }
> = {
  pending: {
    icon: <Clock className="w-3 h-3" />,
    color: 'text-yellow-400',
    label: 'In Attesa',
  },
  processing: {
    icon: <Loader className="w-3 h-3 animate-spin" />,
    color: 'text-blue-400',
    label: 'Elaborazione',
  },
  completed: {
    icon: <CheckCircle className="w-3 h-3" />,
    color: 'text-green-400',
    label: 'Completata',
  },
  failed: {
    icon: <XCircle className="w-3 h-3" />,
    color: 'text-red-400',
    label: 'Fallita',
  },
};

export function RecentQueriesPanel() {
  const { user } = useAuthStore();
  const { loadQuery } = useQueryStore();

  const { data: historyData, isLoading, error } = useQueryHistory(
    user?.id || null,
    { limit: 10, offset: 0 }
  );

  const handleQueryClick = (query: any) => {
    loadQuery({
      trace_id: query.trace_id,
      query: query.query,
      status: query.status,
      timestamp: query.timestamp,
      confidence: query.confidence,
      answer_preview: query.answer_preview,
    });

    // Scroll to top to show the loaded query
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  return (
    <Card className="h-full flex flex-col">
      <CardHeader>
        <CardTitle className="text-base flex items-center gap-2">
          <Clock className="w-4 h-4 text-blue-400" />
          Query Recenti
        </CardTitle>
      </CardHeader>

      <CardContent className="flex-1 overflow-hidden flex flex-col">
        {/* Loading State */}
        {isLoading && (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center space-y-3">
              <Loader className="w-8 h-8 animate-spin text-blue-500 mx-auto" />
              <p className="text-sm text-gray-400">Caricamento cronologia...</p>
            </div>
          </div>
        )}

        {/* Error State */}
        {error && (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center space-y-3">
              <AlertCircle className="w-8 h-8 text-red-400 mx-auto" />
              <p className="text-sm text-gray-400">
                Errore nel caricamento della cronologia
              </p>
            </div>
          </div>
        )}

        {/* Empty State */}
        {!isLoading && !error && (!historyData?.queries || historyData.queries.length === 0) && (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center space-y-3 py-8">
              <div className="w-12 h-12 rounded-full bg-gray-800 flex items-center justify-center mx-auto">
                <Clock className="w-6 h-6 text-gray-600" />
              </div>
              <p className="text-sm text-gray-400">
                Nessuna query recente
              </p>
              <p className="text-xs text-gray-600 max-w-[200px]">
                Le tue query passate appariranno qui per un facile accesso
              </p>
            </div>
          </div>
        )}

        {/* Queries List */}
        {!isLoading && !error && historyData?.queries && historyData.queries.length > 0 && (
          <div className="flex-1 overflow-y-auto space-y-2 pr-2 -mr-2">
            {historyData.queries.map((query) => {
              const statusConfig = STATUS_CONFIG[query.status];

              return (
                <button
                  key={query.trace_id}
                  onClick={() => handleQueryClick(query)}
                  className="w-full text-left p-3 bg-gray-800 hover:bg-gray-700 rounded-lg border border-gray-700 hover:border-blue-600 transition-all group"
                >
                  {/* Query Text */}
                  <p className="text-sm text-white line-clamp-2 mb-2 group-hover:text-blue-300 transition-colors">
                    {query.query}
                  </p>

                  {/* Metadata */}
                  <div className="flex items-center justify-between text-xs">
                    <div className="flex items-center gap-2">
                      {/* Status */}
                      <span className={`flex items-center gap-1 ${statusConfig.color}`}>
                        {statusConfig.icon}
                        <span>{statusConfig.label}</span>
                      </span>

                      {/* Confidence (if available) */}
                      {query.confidence !== null && query.confidence !== undefined && (
                        <>
                          <span className="text-gray-600">•</span>
                          <span className="text-gray-400">
                            {(query.confidence * 100).toFixed(0)}%
                          </span>
                        </>
                      )}
                    </div>

                    {/* Timestamp */}
                    <span className="text-gray-500 tabular-nums">
                      {formatDistanceToNow(new Date(query.timestamp), {
                        addSuffix: true,
                        locale: it,
                      })}
                    </span>
                  </div>

                  {/* Answer Preview (if available) */}
                  {query.answer_preview && (
                    <p className="text-xs text-gray-500 mt-2 line-clamp-1 italic">
                      "{query.answer_preview}..."
                    </p>
                  )}
                </button>
              );
            })}
          </div>
        )}

        {/* Footer Info */}
        {historyData && historyData.queries.length > 0 && (
          <div className="mt-4 pt-3 border-t border-gray-700 text-center">
            <p className="text-xs text-gray-500">
              Mostrando {historyData.queries.length} di {historyData.total_count} query totali
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
