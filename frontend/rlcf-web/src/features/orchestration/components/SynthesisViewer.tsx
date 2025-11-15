/**
 * Synthesis Viewer
 *
 * Displays synthesis result with convergent (single answer) or divergent (multiple positions) modes.
 * Shows uncertainty preservation and alternative interpretations.
 */

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@components/ui/Card';
import { Badge } from '@components/ui/Badge';
import { Button } from '@components/ui/Button';
import { Merge, Split, AlertTriangle, CheckCircle, FileText } from 'lucide-react';

interface LegalBasis {
  norm_id?: string;
  article?: string;
  text?: string;
}

interface AlternativeInterpretation {
  position: string;
  reasoning: string;
  supporting_experts?: string[];
  confidence?: number;
}

interface Answer {
  primary_answer: string;
  confidence: number;
  legal_basis?: LegalBasis[];
  jurisprudence?: any;
  alternative_interpretations?: AlternativeInterpretation[];
  uncertainty_preserved?: boolean;
  consensus_level?: number;
}

interface SynthesisViewerProps {
  answer: Answer;
}

export function SynthesisViewer({ answer }: SynthesisViewerProps) {
  const hasAlternatives = answer.alternative_interpretations && answer.alternative_interpretations.length > 0;
  const isConvergent = !hasAlternatives || answer.consensus_level && answer.consensus_level > 0.8;
  const [viewMode, setViewMode] = useState<'convergent' | 'divergent'>(
    isConvergent ? 'convergent' : 'divergent'
  );

  return (
    <div className="space-y-4">
      {/* Mode Selector */}
      {hasAlternatives && (
        <div className="flex items-center gap-2">
          <Button
            onClick={() => setViewMode('convergent')}
            variant={viewMode === 'convergent' ? 'default' : 'outline'}
            size="sm"
            className="flex items-center gap-2"
          >
            <Merge className="w-4 h-4" />
            Convergent
          </Button>
          <Button
            onClick={() => setViewMode('divergent')}
            variant={viewMode === 'divergent' ? 'default' : 'outline'}
            size="sm"
            className="flex items-center gap-2"
          >
            <Split className="w-4 h-4" />
            Divergent
          </Button>
        </div>
      )}

      {/* Convergent View */}
      {viewMode === 'convergent' && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center justify-between">
              <span className="flex items-center gap-2">
                <Merge className="w-5 h-5" />
                Primary Answer
              </span>
              <div className="flex items-center gap-2">
                {answer.uncertainty_preserved ? (
                  <Badge variant="outline" className="flex items-center gap-1">
                    <AlertTriangle className="w-3 h-3" />
                    Uncertainty Preserved
                  </Badge>
                ) : (
                  <Badge variant="secondary" className="flex items-center gap-1">
                    <CheckCircle className="w-3 h-3" />
                    High Consensus
                  </Badge>
                )}
                <Badge variant="default">
                  {(answer.confidence * 100).toFixed(0)}% confidence
                </Badge>
              </div>
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Primary Answer */}
            <div className="bg-gray-800 p-4 rounded-lg">
              <p className="text-white leading-relaxed">{answer.primary_answer}</p>
            </div>

            {/* Legal Basis */}
            {answer.legal_basis && answer.legal_basis.length > 0 && (
              <div>
                <h4 className="text-sm font-medium text-gray-400 mb-2 flex items-center gap-2">
                  <FileText className="w-4 h-4" />
                  Legal Basis
                </h4>
                <div className="space-y-2">
                  {answer.legal_basis.map((basis, idx) => (
                    <div key={idx} className="p-3 bg-gray-800 rounded border border-gray-700">
                      <div className="flex items-start justify-between gap-2">
                        <div>
                          {basis.norm_id && (
                            <code className="text-sm text-blue-400">{basis.norm_id}</code>
                          )}
                          {basis.article && (
                            <span className="ml-2 text-sm text-gray-300">{basis.article}</span>
                          )}
                        </div>
                      </div>
                      {basis.text && (
                        <p className="mt-2 text-sm text-gray-400 italic">{basis.text}</p>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Consensus Metrics */}
            {answer.consensus_level !== undefined && (
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-gray-800 p-4 rounded-lg">
                  <div className="text-sm text-gray-400 mb-1">Consensus Level</div>
                  <div className="text-2xl font-semibold text-white">
                    {(answer.consensus_level * 100).toFixed(0)}%
                  </div>
                </div>
                <div className="bg-gray-800 p-4 rounded-lg">
                  <div className="text-sm text-gray-400 mb-1">Expert Agreement</div>
                  <div className="text-2xl font-semibold text-white">
                    {answer.consensus_level > 0.8 ? 'High' : answer.consensus_level > 0.5 ? 'Moderate' : 'Low'}
                  </div>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Divergent View */}
      {viewMode === 'divergent' && hasAlternatives && (
        <div className="space-y-4">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <Split className="w-5 h-5" />
                Multiple Positions Detected
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="mb-4 p-4 bg-orange-500/10 border border-orange-500/30 rounded-lg">
                <p className="text-sm text-orange-300">
                  <strong>Divergent Synthesis:</strong> Experts have identified {answer.alternative_interpretations!.length + 1} distinct legal positions.
                  Review each position below to understand the range of valid interpretations.
                </p>
              </div>

              {/* Primary Position */}
              <div className="mb-4">
                <h4 className="text-sm font-medium text-gray-400 mb-3 flex items-center gap-2">
                  <Badge variant="default">Position 1 (Primary)</Badge>
                  {(answer.confidence * 100).toFixed(0)}% confidence
                </h4>
                <div className="p-4 bg-gray-800 rounded-lg border-2 border-blue-500/50">
                  <p className="text-white leading-relaxed">{answer.primary_answer}</p>
                </div>
              </div>

              {/* Alternative Positions */}
              {answer.alternative_interpretations!.map((alt, idx) => (
                <div key={idx} className="mb-4">
                  <h4 className="text-sm font-medium text-gray-400 mb-3 flex items-center gap-2">
                    <Badge variant="outline">Position {idx + 2}</Badge>
                    {alt.confidence && `${(alt.confidence * 100).toFixed(0)}% confidence`}
                    {alt.supporting_experts && alt.supporting_experts.length > 0 && (
                      <span className="text-gray-500">
                        • Supported by {alt.supporting_experts.length} expert(s)
                      </span>
                    )}
                  </h4>
                  <div className="p-4 bg-gray-800 rounded-lg border border-gray-700 space-y-3">
                    <div>
                      <h5 className="text-sm font-medium text-gray-400 mb-1">Position</h5>
                      <p className="text-white">{alt.position}</p>
                    </div>
                    <div>
                      <h5 className="text-sm font-medium text-gray-400 mb-1">Reasoning</h5>
                      <p className="text-gray-300 text-sm leading-relaxed">{alt.reasoning}</p>
                    </div>
                    {alt.supporting_experts && alt.supporting_experts.length > 0 && (
                      <div>
                        <h5 className="text-sm font-medium text-gray-400 mb-2">Supporting Experts</h5>
                        <div className="flex flex-wrap gap-2">
                          {alt.supporting_experts.map((expert, i) => (
                            <Badge key={i} variant="secondary" size="sm">
                              {expert.replace(/_/g, ' ')}
                            </Badge>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              ))}

              {/* Shannon Entropy Visualization (placeholder) */}
              <div className="mt-6 p-4 bg-gray-800 rounded-lg">
                <h4 className="text-sm font-medium text-gray-400 mb-3">Uncertainty Metrics</h4>
                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <div className="text-xs text-gray-500 mb-1">Positions</div>
                    <div className="text-xl font-semibold text-white">
                      {answer.alternative_interpretations!.length + 1}
                    </div>
                  </div>
                  <div>
                    <div className="text-xs text-gray-500 mb-1">Entropy</div>
                    <div className="text-xl font-semibold text-white">
                      {/* TODO: Calculate Shannon entropy from position distribution */}
                      N/A
                    </div>
                  </div>
                  <div>
                    <div className="text-xs text-gray-500 mb-1">Disagreement</div>
                    <div className="text-xl font-semibold text-white">
                      {answer.uncertainty_preserved ? 'High' : 'Low'}
                    </div>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* No Alternatives Message */}
      {viewMode === 'divergent' && !hasAlternatives && (
        <Card>
          <CardContent className="py-8 text-center">
            <CheckCircle className="w-12 h-12 mx-auto mb-3 text-green-400" />
            <h4 className="text-lg font-medium text-white mb-2">Convergent Synthesis</h4>
            <p className="text-gray-400">
              All experts converged on a single position. No alternative interpretations were identified.
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
