/**
 * Answer Display Component
 *
 * Displays the primary legal answer with Markdown rendering, confidence meter,
 * and uncertainty preservation indicator.
 */

import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Card, CardHeader, CardTitle, CardContent } from '@components/ui/Card';
import { Badge } from '@components/ui/Badge';
import { Button } from '@components/ui/Button';
import { Copy, Check, AlertCircle } from 'lucide-react';
import type { Answer } from '@/types/orchestration';

interface AnswerDisplayProps {
  answer: Answer;
}

export function AnswerDisplay({ answer }: AnswerDisplayProps) {
  const [copied, setCopied] = useState(false);

  const handleCopyAnswer = async () => {
    try {
      await navigator.clipboard.writeText(answer.primary_answer);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy answer:', err);
    }
  };

  // Calculate confidence color
  const getConfidenceColor = (confidence: number): string => {
    if (confidence >= 0.8) return 'bg-green-500';
    if (confidence >= 0.6) return 'bg-yellow-500';
    return 'bg-orange-500';
  };

  const getConfidenceTextColor = (confidence: number): string => {
    if (confidence >= 0.8) return 'text-green-400';
    if (confidence >= 0.6) return 'text-yellow-400';
    return 'text-orange-400';
  };

  const confidencePercentage = (answer.confidence * 100).toFixed(1);

  return (
    <Card>
      <CardHeader>
        <div className="flex items-start justify-between">
          <CardTitle className="text-xl">Risposta Legale</CardTitle>
          <Button
            variant="ghost"
            size="sm"
            onClick={handleCopyAnswer}
            className="flex items-center gap-2"
          >
            {copied ? (
              <>
                <Check className="w-4 h-4 text-green-400" />
                <span className="text-green-400">Copiato!</span>
              </>
            ) : (
              <>
                <Copy className="w-4 h-4" />
                Copia
              </>
            )}
          </Button>
        </div>
      </CardHeader>

      <CardContent className="space-y-6">
        {/* Confidence Meter */}
        <div className="space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className="text-gray-400 font-medium">Confidenza della Risposta</span>
            <span className={`font-semibold ${getConfidenceTextColor(answer.confidence)}`}>
              {confidencePercentage}%
            </span>
          </div>
          <div className="w-full h-2 bg-gray-800 rounded-full overflow-hidden">
            <div
              className={`h-full ${getConfidenceColor(answer.confidence)} transition-all duration-500`}
              style={{ width: `${confidencePercentage}%` }}
            />
          </div>
          <p className="text-xs text-gray-500">
            La confidenza riflette la coerenza tra gli esperti consultati e la qualità delle fonti.
          </p>
        </div>

        {/* Uncertainty Preserved Badge */}
        {answer.uncertainty_preserved && (
          <div className="flex items-start gap-3 p-4 bg-blue-500/10 border border-blue-500/30 rounded-lg">
            <AlertCircle className="w-5 h-5 text-blue-400 mt-0.5 flex-shrink-0" />
            <div className="flex-1">
              <div className="flex items-center gap-2 mb-1">
                <Badge variant="outline" className="border-blue-500/50 text-blue-300">
                  Incertezza Preservata
                </Badge>
              </div>
              <p className="text-sm text-blue-200">
                Sono state rilevate divergenze interpretative tra gli esperti. Le interpretazioni
                alternative sono disponibili sotto la risposta principale.
              </p>
            </div>
          </div>
        )}

        {/* Consensus Level (if available) */}
        {answer.consensus_level !== null && answer.consensus_level !== undefined && (
          <div className="flex items-center justify-between p-3 bg-gray-800 rounded-lg">
            <span className="text-sm text-gray-400">Livello di Consenso tra Esperti</span>
            <span className="text-sm font-semibold text-white">
              {(answer.consensus_level * 100).toFixed(0)}%
            </span>
          </div>
        )}

        {/* Answer Content with Markdown */}
        <div className="prose prose-invert prose-sm max-w-none">
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              // Custom styling for markdown elements
              h1: ({ node, ...props }) => (
                <h1 className="text-2xl font-bold text-white mb-4 mt-6" {...props} />
              ),
              h2: ({ node, ...props }) => (
                <h2 className="text-xl font-semibold text-white mb-3 mt-5" {...props} />
              ),
              h3: ({ node, ...props }) => (
                <h3 className="text-lg font-semibold text-gray-200 mb-2 mt-4" {...props} />
              ),
              p: ({ node, ...props }) => (
                <p className="text-gray-300 leading-relaxed mb-4" {...props} />
              ),
              ul: ({ node, ...props }) => (
                <ul className="list-disc list-inside space-y-2 text-gray-300 mb-4" {...props} />
              ),
              ol: ({ node, ...props }) => (
                <ol className="list-decimal list-inside space-y-2 text-gray-300 mb-4" {...props} />
              ),
              li: ({ node, ...props }) => <li className="ml-4" {...props} />,
              blockquote: ({ node, ...props }) => (
                <blockquote
                  className="border-l-4 border-blue-500 pl-4 italic text-gray-400 my-4"
                  {...props}
                />
              ),
              code: ({ node, inline, ...props }: any) =>
                inline ? (
                  <code
                    className="px-1.5 py-0.5 bg-gray-800 text-blue-300 rounded text-sm font-mono"
                    {...props}
                  />
                ) : (
                  <code
                    className="block p-4 bg-gray-900 text-gray-300 rounded-lg overflow-x-auto font-mono text-sm"
                    {...props}
                  />
                ),
              strong: ({ node, ...props }) => (
                <strong className="font-semibold text-white" {...props} />
              ),
              em: ({ node, ...props }) => <em className="italic text-gray-400" {...props} />,
              a: ({ node, ...props }) => (
                <a
                  className="text-blue-400 hover:text-blue-300 underline transition-colors"
                  target="_blank"
                  rel="noopener noreferrer"
                  {...props}
                />
              ),
              table: ({ node, ...props }) => (
                <div className="overflow-x-auto mb-4">
                  <table
                    className="min-w-full divide-y divide-gray-700 border border-gray-700"
                    {...props}
                  />
                </div>
              ),
              th: ({ node, ...props }) => (
                <th
                  className="px-4 py-2 bg-gray-800 text-left text-sm font-semibold text-white"
                  {...props}
                />
              ),
              td: ({ node, ...props }) => (
                <td className="px-4 py-2 text-sm text-gray-300 border-t border-gray-700" {...props} />
              ),
            }}
          >
            {answer.primary_answer}
          </ReactMarkdown>
        </div>

        {/* Footer Note */}
        <div className="pt-4 border-t border-gray-700 text-xs text-gray-500">
          <p>
            Questa risposta è stata generata consultando <strong className="text-gray-400">4 esperti legali AI</strong>
            {' '}(Interpretazione Letterale, Sistematico-Teleologica, Bilanciamento Principi, Analisi
            Precedenti) e sintetizzata secondo il principio RLCF (Reinforcement Learning from
            Community Feedback).
          </p>
        </div>
      </CardContent>
    </Card>
  );
}
