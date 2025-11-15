/**
 * Alternative Interpretations Panel Component
 *
 * Displays divergent legal interpretations when RLCF uncertainty is preserved.
 * Shows minority, contested, or emerging positions with supporting experts and sources.
 */

import { useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@components/ui/Card';
import { Badge } from '@components/ui/Badge';
import { AlertTriangle, Users, Scale, Gavel, ChevronDown } from 'lucide-react';
import type { AlternativeInterpretation } from '@/types/orchestration';

interface AlternativeInterpretationsPanelProps {
  interpretations: AlternativeInterpretation[];
}

export function AlternativeInterpretationsPanel({
  interpretations,
}: AlternativeInterpretationsPanelProps) {
  if (!interpretations || interpretations.length === 0) {
    return null;
  }

  return (
    <Card className="border-yellow-500/30">
      <CardHeader>
        <div className="flex items-start gap-3">
          <AlertTriangle className="w-5 h-5 text-yellow-400 mt-0.5 flex-shrink-0" />
          <div className="flex-1">
            <CardTitle className="text-yellow-300">Interpretazioni Alternative</CardTitle>
            <p className="text-sm text-yellow-200/80 mt-2">
              Sono state rilevate divergenze interpretative tra gli esperti. Queste posizioni
              alternative possono essere rilevanti per una valutazione completa del caso.
            </p>
          </div>
        </div>
      </CardHeader>

      <CardContent>
        <div className="space-y-5">
          {interpretations.map((interpretation, index) => (
            <InterpretationCard key={index} interpretation={interpretation} index={index} />
          ))}
        </div>

        {/* RLCF Explanation */}
        <div className="mt-6 pt-4 border-t border-yellow-500/30 text-xs text-yellow-200/70">
          <p>
            <strong className="text-yellow-300">Principio RLCF:</strong> Le divergenze
            interpretative non sono errori, ma riflettono la complessità intrinseca del diritto.
            Preservare l'incertezza fornisce trasparenza e consente valutazioni più informate.
          </p>
        </div>
      </CardContent>
    </Card>
  );
}

interface InterpretationCardProps {
  interpretation: AlternativeInterpretation;
  index: number;
}

function InterpretationCard({ interpretation, index }: InterpretationCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  // Get support level styling
  const getSupportLevelConfig = (
    level: 'minority' | 'contested' | 'emerging'
  ): { label: string; color: string; description: string } => {
    switch (level) {
      case 'minority':
        return {
          label: 'Posizione Minoritaria',
          color: 'bg-orange-500/20 border-orange-500/40 text-orange-300',
          description: 'Sostenuta da una minoranza di esperti',
        };
      case 'contested':
        return {
          label: 'Posizione Contestata',
          color: 'bg-yellow-500/20 border-yellow-500/40 text-yellow-300',
          description: 'Dibattuta tra gli esperti con sostanziale divisione',
        };
      case 'emerging':
        return {
          label: 'Posizione Emergente',
          color: 'bg-blue-500/20 border-blue-500/40 text-blue-300',
          description: 'Nuova interpretazione in fase di consolidamento',
        };
    }
  };

  const supportConfig = getSupportLevelConfig(interpretation.support_level);

  return (
    <div className="border border-gray-700 rounded-lg p-4 bg-gray-800/50">
      {/* Header */}
      <div className="flex items-start justify-between gap-4 mb-3">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-2">
            <span className="text-sm font-semibold text-gray-400">
              Interpretazione #{index + 1}
            </span>
            <Badge variant="outline" className={supportConfig.color}>
              {supportConfig.label}
            </Badge>
          </div>

          <h4 className="text-base font-semibold text-white mb-1">{interpretation.position}</h4>
          <p className="text-xs text-gray-500">{supportConfig.description}</p>
        </div>
      </div>

      {/* Supporting Experts */}
      {interpretation.supporting_experts && interpretation.supporting_experts.length > 0 && (
        <div className="mb-3">
          <div className="flex items-center gap-2 text-xs text-gray-400 mb-2">
            <Users className="w-3.5 h-3.5" />
            <span>Esperti a sostegno ({interpretation.supporting_experts.length})</span>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {interpretation.supporting_experts.map((expert, idx) => (
              <Badge key={idx} variant="secondary">
                {expert}
              </Badge>
            ))}
          </div>
        </div>
      )}

      {/* Supporting Sources */}
      <div className="space-y-2 mb-3">
        {/* Norms */}
        {interpretation.supporting_norms && interpretation.supporting_norms.length > 0 && (
          <div>
            <div className="flex items-center gap-2 text-xs text-gray-400 mb-1.5">
              <Scale className="w-3.5 h-3.5" />
              <span>Norme a sostegno ({interpretation.supporting_norms.length})</span>
            </div>
            <div className="flex flex-wrap gap-1.5">
              {interpretation.supporting_norms.map((norm, idx) => (
                <Badge key={idx} variant="outline">
                  {norm}
                </Badge>
              ))}
            </div>
          </div>
        )}

        {/* Jurisprudence */}
        {interpretation.supporting_jurisprudence &&
          interpretation.supporting_jurisprudence.length > 0 && (
            <div>
              <div className="flex items-center gap-2 text-xs text-gray-400 mb-1.5">
                <Gavel className="w-3.5 h-3.5" />
                <span>Giurisprudenza a sostegno ({interpretation.supporting_jurisprudence.length})</span>
              </div>
              <div className="flex flex-wrap gap-1.5">
                {interpretation.supporting_jurisprudence.map((case_, idx) => (
                  <Badge key={idx} variant="outline">
                    {case_}
                  </Badge>
                ))}
              </div>
            </div>
          )}
      </div>

      {/* Reasoning (collapsible) */}
      {interpretation.reasoning && (
        <div>
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="flex items-center gap-2 text-sm text-blue-400 hover:text-blue-300 transition-colors mb-2"
          >
            <ChevronDown
              className={`w-4 h-4 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
            />
            {isExpanded ? 'Nascondi' : 'Mostra'} ragionamento
          </button>

          {isExpanded && (
            <div className="p-3 bg-gray-900/70 rounded-lg border border-gray-700">
              <h5 className="text-xs font-semibold text-gray-400 uppercase mb-2">
                Ragionamento a Sostegno
              </h5>
              <p className="text-sm text-gray-300 leading-relaxed">{interpretation.reasoning}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
