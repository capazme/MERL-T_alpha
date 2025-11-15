/**
 * Jurisprudence Panel Component
 *
 * Displays case law (giurisprudenza) cited in the answer, with court, date,
 * summary (massima), relevance score, and external links.
 */

import { useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@components/ui/Card';
import { Badge } from '@components/ui/Badge';
import { ExternalLink, Gavel, Calendar, ChevronDown } from 'lucide-react';
import type { Jurisprudence } from '@/types/orchestration';

interface JurisprudencePanelProps {
  jurisprudence: Jurisprudence[];
}

export function JurisprudencePanel({ jurisprudence }: JurisprudencePanelProps) {
  if (!jurisprudence || jurisprudence.length === 0) {
    return null;
  }

  // Sort by relevance descending
  const sortedJurisprudence = [...jurisprudence].sort((a, b) => b.relevance - a.relevance);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Gavel className="w-5 h-5 text-purple-400" />
          Giurisprudenza Citata
        </CardTitle>
        <p className="text-sm text-gray-400 mt-2">
          Sentenze e decisioni giurisprudenziali rilevanti
        </p>
      </CardHeader>

      <CardContent>
        <div className="space-y-4">
          {sortedJurisprudence.map((case_, index) => (
            <JurisprudenceCard key={index} case_={case_} />
          ))}
        </div>

        {/* Summary */}
        <div className="mt-6 pt-4 border-t border-gray-700 text-xs text-gray-500">
          <p>
            Totale sentenze citate: <strong className="text-gray-400">{jurisprudence.length}</strong>
          </p>
        </div>
      </CardContent>
    </Card>
  );
}

interface JurisprudenceCardProps {
  case_: Jurisprudence;
}

function JurisprudenceCard({ case_ }: JurisprudenceCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  // Get relevance color
  const getRelevanceColor = (relevance: number): string => {
    if (relevance >= 0.8) return 'text-green-400';
    if (relevance >= 0.6) return 'text-yellow-400';
    return 'text-orange-400';
  };

  const getRelevanceBgColor = (relevance: number): string => {
    if (relevance >= 0.8) return 'bg-green-500/20 border-green-500/30';
    if (relevance >= 0.6) return 'bg-yellow-500/20 border-yellow-500/30';
    return 'bg-orange-500/20 border-orange-500/30';
  };

  // Determine court level from court name
  const getCourtLevel = (court: string): string => {
    const lowerCourt = court.toLowerCase();
    if (lowerCourt.includes('cassazione') || lowerCourt.includes('cass.')) return 'Cassazione';
    if (lowerCourt.includes('costituzionale') || lowerCourt.includes('corte cost.')) return 'Corte Costituzionale';
    if (lowerCourt.includes('appello')) return 'Appello';
    if (lowerCourt.includes('tribunale') || lowerCourt.includes('trib.')) return 'Tribunale';
    if (lowerCourt.includes('tar')) return 'TAR';
    if (lowerCourt.includes('consiglio di stato')) return 'Consiglio di Stato';
    return 'Altro';
  };

  const courtLevel = getCourtLevel(case_.court);

  // Format date
  const formatDate = (dateStr: string | null | undefined): string => {
    if (!dateStr) return 'Data non disponibile';
    try {
      const date = new Date(dateStr);
      return date.toLocaleDateString('it-IT', {
        year: 'numeric',
        month: 'long',
        day: 'numeric',
      });
    } catch {
      return dateStr;
    }
  };

  const formattedDate = formatDate(case_.date);

  return (
    <div className={`border rounded-lg p-4 ${getRelevanceBgColor(case_.relevance)}`}>
      {/* Header */}
      <div className="flex items-start justify-between gap-4 mb-3">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            <Badge variant="outline">
              {courtLevel}
            </Badge>
            {case_.date && (
              <div className="flex items-center gap-1 text-xs text-gray-400">
                <Calendar className="w-3 h-3" />
                <span>{formattedDate}</span>
              </div>
            )}
          </div>

          <h4 className="text-base font-semibold text-white">{case_.court}</h4>
          <p className="text-sm text-gray-400 mt-1">ID: {case_.case_id}</p>
        </div>

        {/* Relevance Score */}
        <div className="flex flex-col items-end gap-1">
          <span className={`text-xs font-medium ${getRelevanceColor(case_.relevance)}`}>
            Rilevanza
          </span>
          <span className={`text-lg font-bold ${getRelevanceColor(case_.relevance)}`}>
            {(case_.relevance * 100).toFixed(0)}%
          </span>
        </div>
      </div>

      {/* Summary (Massima) */}
      {case_.summary && (
        <div className="mb-3">
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="flex items-center gap-2 text-sm text-purple-400 hover:text-purple-300 transition-colors"
          >
            <ChevronDown
              className={`w-4 h-4 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
            />
            {isExpanded ? 'Nascondi' : 'Mostra'} massima
          </button>

          {isExpanded && (
            <div className="mt-3 p-3 bg-gray-900/50 rounded-lg border border-gray-700">
              <h5 className="text-xs font-semibold text-gray-400 uppercase mb-2">Massima</h5>
              <p className="text-sm text-gray-300 leading-relaxed">{case_.summary}</p>
            </div>
          )}
        </div>
      )}

      {/* External Link */}
      {case_.link && (
        <div className="flex items-center gap-2">
          <a
            href={case_.link}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 text-xs text-purple-400 hover:text-purple-300 transition-colors"
          >
            <ExternalLink className="w-3.5 h-3.5" />
            Consulta sentenza completa
          </a>
        </div>
      )}
    </div>
  );
}
