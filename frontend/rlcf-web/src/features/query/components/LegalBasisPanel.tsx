/**
 * Legal Basis Panel Component
 *
 * Displays the legal norms (normativa) cited in the answer, with relevance scores,
 * article references, and optional links to Normattiva.
 */

import { useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@components/ui/Card';
import { Badge } from '@components/ui/Badge';
import { Collapsible } from '@components/ui/Collapsible';
import { ExternalLink, Scale, ChevronDown } from 'lucide-react';
import type { LegalBasis } from '@/types/orchestration';

interface LegalBasisPanelProps {
  legalBasis: LegalBasis[];
}

export function LegalBasisPanel({ legalBasis }: LegalBasisPanelProps) {
  if (!legalBasis || legalBasis.length === 0) {
    return null;
  }

  // Sort by relevance descending
  const sortedBasis = [...legalBasis].sort((a, b) => b.relevance - a.relevance);

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Scale className="w-5 h-5 text-blue-400" />
          Fondamento Normativo
        </CardTitle>
        <p className="text-sm text-gray-400 mt-2">
          Norme e articoli di legge citati a supporto della risposta
        </p>
      </CardHeader>

      <CardContent>
        <div className="space-y-4">
          {sortedBasis.map((basis, index) => (
            <LegalBasisCard key={index} basis={basis} />
          ))}
        </div>

        {/* Summary */}
        <div className="mt-6 pt-4 border-t border-gray-700 text-xs text-gray-500">
          <p>
            Totale norme citate: <strong className="text-gray-400">{legalBasis.length}</strong>
          </p>
        </div>
      </CardContent>
    </Card>
  );
}

interface LegalBasisCardProps {
  basis: LegalBasis;
}

function LegalBasisCard({ basis }: LegalBasisCardProps) {
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

  // Determine norm type from title
  const getNormType = (title: string): string => {
    const lowerTitle = title.toLowerCase();
    if (lowerTitle.includes('costituzione')) return 'Costituzione';
    if (lowerTitle.includes('codice civile')) return 'Codice Civile';
    if (lowerTitle.includes('codice penale')) return 'Codice Penale';
    if (lowerTitle.includes('codice procedura civile')) return 'Cod. Proc. Civile';
    if (lowerTitle.includes('codice procedura penale')) return 'Cod. Proc. Penale';
    if (lowerTitle.includes('decreto legislativo') || lowerTitle.includes('d.lgs')) return 'D.Lgs.';
    if (lowerTitle.includes('decreto legge') || lowerTitle.includes('d.l.')) return 'D.L.';
    if (lowerTitle.includes('legge')) return 'Legge';
    return 'Norma';
  };

  const normType = getNormType(basis.norm_title);

  // Build Normattiva link (if norm_id looks like a valid identifier)
  const buildNormativaLink = (): string | null => {
    // This is a simplified heuristic - real implementation would parse norm_id properly
    // Example norm_id format: "CC_ART_2043" or "COST_ART_3"
    // Normattiva URLs are complex and vary by norm type
    // For now, return a generic search URL
    if (basis.norm_id) {
      return `https://www.normattiva.it/do/ricerca/advancedRicercaFull?keyword=${encodeURIComponent(basis.norm_title)}`;
    }
    return null;
  };

  const normativaLink = buildNormativaLink();

  return (
    <div className={`border rounded-lg p-4 ${getRelevanceBgColor(basis.relevance)}`}>
      {/* Header */}
      <div className="flex items-start justify-between gap-4 mb-3">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            <Badge variant="outline">
              {normType}
            </Badge>
            {basis.article && (
              <Badge variant="secondary">
                {basis.article}
              </Badge>
            )}
          </div>

          <h4 className="text-base font-semibold text-white">{basis.norm_title}</h4>
        </div>

        {/* Relevance Score */}
        <div className="flex flex-col items-end gap-1">
          <span className={`text-xs font-medium ${getRelevanceColor(basis.relevance)}`}>
            Rilevanza
          </span>
          <span className={`text-lg font-bold ${getRelevanceColor(basis.relevance)}`}>
            {(basis.relevance * 100).toFixed(0)}%
          </span>
        </div>
      </div>

      {/* Excerpt (if available) */}
      {basis.excerpt && (
        <div className="mb-3">
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="flex items-center gap-2 text-sm text-blue-400 hover:text-blue-300 transition-colors"
          >
            <ChevronDown
              className={`w-4 h-4 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
            />
            {isExpanded ? 'Nascondi' : 'Mostra'} estratto
          </button>

          {isExpanded && (
            <div className="mt-3 p-3 bg-gray-900/50 rounded-lg border border-gray-700">
              <p className="text-sm text-gray-300 italic leading-relaxed">"{basis.excerpt}"</p>
            </div>
          )}
        </div>
      )}

      {/* External Link */}
      {normativaLink && (
        <div className="flex items-center gap-2">
          <a
            href={normativaLink}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 text-xs text-blue-400 hover:text-blue-300 transition-colors"
          >
            <ExternalLink className="w-3.5 h-3.5" />
            Consulta su Normattiva
          </a>
        </div>
      )}
    </div>
  );
}
