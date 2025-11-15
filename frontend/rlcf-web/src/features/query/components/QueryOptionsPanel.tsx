/**
 * Query Options Panel Component
 *
 * Configuration panel for query execution options:
 * - Max iterations (1-10)
 * - Timeout (10-120 seconds)
 * - Return execution trace (boolean)
 */

import { Collapsible } from '@components/ui/Collapsible';
import { Badge } from '@components/ui/Badge';
import { Sliders, Info } from 'lucide-react';
import { useQueryStore } from '@/app/store/query';

interface QueryOptionsPanelProps {
  defaultOpen?: boolean;
}

export function QueryOptionsPanel({ defaultOpen = false }: QueryOptionsPanelProps) {
  const { queryOptions, updateOptions } = useQueryStore();

  const handleMaxIterationsChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = parseInt(e.target.value, 10);
    updateOptions({ max_iterations: value });
  };

  const handleTimeoutChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = parseInt(e.target.value, 10);
    updateOptions({ timeout_ms: value * 1000 }); // Convert seconds to ms
  };

  const handleReturnTraceChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    updateOptions({ return_trace: e.target.checked });
  };

  const timeoutSeconds = (queryOptions.timeout_ms || 30000) / 1000;

  return (
    <Collapsible
      title="Opzioni Esecuzione"
      defaultOpen={defaultOpen}
      icon={<Sliders className="w-4 h-4" />}
      badge={
        <Badge variant="outline" size="sm">
          Avanzate
        </Badge>
      }
    >
      <div className="space-y-6">
        <p className="text-sm text-gray-400">
          Personalizza i parametri di esecuzione della query per bilanciare accuratezza e
          velocità di risposta.
        </p>

        {/* Max Iterations */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <label className="text-sm font-medium text-gray-300">
              Iterazioni Massime
            </label>
            <span className="text-sm font-mono text-blue-400">
              {queryOptions.max_iterations || 3}
            </span>
          </div>

          <input
            type="range"
            min="1"
            max="10"
            step="1"
            value={queryOptions.max_iterations || 3}
            onChange={handleMaxIterationsChange}
            className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-blue-500"
          />

          <div className="flex items-start gap-2 text-xs text-gray-500">
            <Info className="w-3.5 h-3.5 mt-0.5 flex-shrink-0" />
            <p>
              Numero massimo di raffinamenti iterativi. Più iterazioni aumentano
              l'accuratezza ma richiedono più tempo.
            </p>
          </div>

          <div className="flex items-center justify-between text-xs text-gray-600">
            <span>Veloce (1)</span>
            <span>Bilanciato (3-5)</span>
            <span>Approfondito (10)</span>
          </div>
        </div>

        {/* Timeout */}
        <div className="space-y-3">
          <div className="flex items-center justify-between">
            <label className="text-sm font-medium text-gray-300">
              Timeout Esecuzione
            </label>
            <span className="text-sm font-mono text-blue-400">
              {timeoutSeconds}s
            </span>
          </div>

          <input
            type="range"
            min="10"
            max="120"
            step="10"
            value={timeoutSeconds}
            onChange={handleTimeoutChange}
            className="w-full h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-blue-500"
          />

          <div className="flex items-start gap-2 text-xs text-gray-500">
            <Info className="w-3.5 h-3.5 mt-0.5 flex-shrink-0" />
            <p>
              Tempo massimo di attesa per la risposta. Query complesse potrebbero
              richiedere timeout più alti.
            </p>
          </div>

          <div className="flex items-center justify-between text-xs text-gray-600">
            <span>10s</span>
            <span>60s</span>
            <span>120s</span>
          </div>
        </div>

        {/* Return Trace */}
        <div className="space-y-3">
          <label className="flex items-start gap-3 cursor-pointer group">
            <input
              type="checkbox"
              checked={queryOptions.return_trace ?? true}
              onChange={handleReturnTraceChange}
              className="mt-1 w-4 h-4 text-blue-600 bg-gray-700 border-gray-600 rounded focus:ring-blue-500 focus:ring-2 cursor-pointer"
            />
            <div className="flex-1">
              <div className="text-sm font-medium text-gray-300 group-hover:text-white transition-colors">
                Includi Traccia di Esecuzione
              </div>
              <p className="text-xs text-gray-500 mt-1">
                Mostra il percorso completo di elaborazione: esperti consultati, agenti
                utilizzati, stage eseguiti, e metriche di performance. Utile per
                trasparenza e debugging.
              </p>
            </div>
          </label>
        </div>

        {/* Execution Preview */}
        <div className="pt-4 border-t border-gray-700">
          <h4 className="text-sm font-medium text-gray-300 mb-3">
            Configurazione Corrente
          </h4>
          <div className="bg-gray-800/50 rounded-lg p-3 space-y-2 text-xs font-mono">
            <div className="flex items-center justify-between">
              <span className="text-gray-400">max_iterations:</span>
              <span className="text-blue-400">{queryOptions.max_iterations || 3}</span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-gray-400">timeout_ms:</span>
              <span className="text-blue-400">
                {queryOptions.timeout_ms || 30000}
              </span>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-gray-400">return_trace:</span>
              <span
                className={
                  queryOptions.return_trace !== false
                    ? 'text-green-400'
                    : 'text-red-400'
                }
              >
                {queryOptions.return_trace !== false ? 'true' : 'false'}
              </span>
            </div>
          </div>

          <p className="text-xs text-gray-500 mt-3">
            Tempo stimato di risposta:{' '}
            <span className="text-blue-400 font-medium">
              {Math.ceil(
                ((queryOptions.max_iterations || 3) * 8 +
                  (queryOptions.return_trace !== false ? 2 : 0)) *
                  0.8
              )}
              -
              {Math.ceil(
                ((queryOptions.max_iterations || 3) * 12 +
                  (queryOptions.return_trace !== false ? 3 : 0)) *
                  1.2
              )}
              s
            </span>
          </p>
        </div>
      </div>
    </Collapsible>
  );
}
