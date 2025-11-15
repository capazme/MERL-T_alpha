/**
 * Expert Opinion Panel
 *
 * Displays individual expert opinions on a query result.
 * Shows the 4 expert types (Literal, Systemic, Principles, Precedent) with their reasoning.
 */

import { Card, CardContent, CardHeader, CardTitle } from '@components/ui/Card';
import { Badge } from '@components/ui/Badge';
import { Brain, Scale, BookOpen, Gavel, TrendingUp } from 'lucide-react';

interface ExpertOpinion {
  expert_type: string;
  reasoning?: string;
  confidence?: number;
  position?: string;
  supporting_evidence?: string[];
}

interface ExpertOpinionPanelProps {
  experts: string[]; // List of expert types consulted
  opinions?: ExpertOpinion[]; // Detailed opinions (if available)
}

const expertConfig: Record<string, { icon: React.ReactNode; color: string; description: string }> = {
  literal_interpreter: {
    icon: <BookOpen className="w-5 h-5" />,
    color: 'text-blue-400',
    description: 'Interprets legal text strictly according to its literal meaning',
  },
  systemic_teleological: {
    icon: <TrendingUp className="w-5 h-5" />,
    color: 'text-purple-400',
    description: 'Analyzes purpose and systematic context of legal norms',
  },
  principles_balancer: {
    icon: <Scale className="w-5 h-5" />,
    color: 'text-green-400',
    description: 'Balances competing legal principles and constitutional values',
  },
  precedent_analyst: {
    icon: <Gavel className="w-5 h-5" />,
    color: 'text-orange-400',
    description: 'Analyzes case law and judicial precedents',
  },
};

export function ExpertOpinionPanel({ experts, opinions }: ExpertOpinionPanelProps) {
  // If detailed opinions not available, show consulted experts list
  const hasDetailedOpinions = opinions && opinions.length > 0;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Brain className="w-5 h-5" />
          Expert Opinions ({experts.length})
        </CardTitle>
      </CardHeader>
      <CardContent>
        {!hasDetailedOpinions ? (
          // Fallback: Show consulted experts
          <div className="space-y-3">
            <p className="text-sm text-gray-400 mb-4">
              The following experts were consulted for this query:
            </p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {experts.map((expertType) => {
                const config = expertConfig[expertType] || {
                  icon: <Brain className="w-5 h-5" />,
                  color: 'text-gray-400',
                  description: 'Expert analysis',
                };

                return (
                  <div
                    key={expertType}
                    className="flex items-start gap-3 p-4 bg-gray-800 rounded-lg border border-gray-700 hover:border-gray-600 transition-colors"
                  >
                    <div className={`${config.color} mt-1`}>{config.icon}</div>
                    <div className="flex-1">
                      <h4 className="font-medium text-white capitalize mb-1">
                        {expertType.replace(/_/g, ' ')}
                      </h4>
                      <p className="text-sm text-gray-400">{config.description}</p>
                      <Badge variant="outline" className="mt-2">
                        Consulted
                      </Badge>
                    </div>
                  </div>
                );
              })}
            </div>

            <div className="mt-6 p-4 bg-blue-500/10 border border-blue-500/30 rounded-lg">
              <p className="text-sm text-blue-300">
                <strong>Note:</strong> Detailed expert opinions are available in the full execution trace.
                Future versions will display individual reasoning, confidence scores, and supporting evidence here.
              </p>
            </div>
          </div>
        ) : (
          // Detailed opinions view
          <div className="space-y-4">
            {opinions.map((opinion, idx) => {
              const config = expertConfig[opinion.expert_type] || {
                icon: <Brain className="w-5 h-5" />,
                color: 'text-gray-400',
                description: '',
              };

              return (
                <Card key={idx} className="bg-gray-800 border-gray-700">
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <div className={config.color}>{config.icon}</div>
                        <h4 className="font-medium text-white capitalize">
                          {opinion.expert_type.replace(/_/g, ' ')}
                        </h4>
                      </div>
                      {opinion.confidence && (
                        <Badge variant="secondary">
                          {(opinion.confidence * 100).toFixed(0)}% confidence
                        </Badge>
                      )}
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    {opinion.position && (
                      <div>
                        <h5 className="text-sm font-medium text-gray-400 mb-1">Position</h5>
                        <p className="text-white">{opinion.position}</p>
                      </div>
                    )}

                    {opinion.reasoning && (
                      <div>
                        <h5 className="text-sm font-medium text-gray-400 mb-1">Reasoning</h5>
                        <p className="text-gray-300 text-sm leading-relaxed">{opinion.reasoning}</p>
                      </div>
                    )}

                    {opinion.supporting_evidence && opinion.supporting_evidence.length > 0 && (
                      <div>
                        <h5 className="text-sm font-medium text-gray-400 mb-2">Supporting Evidence</h5>
                        <ul className="space-y-1">
                          {opinion.supporting_evidence.map((evidence, i) => (
                            <li key={i} className="text-sm text-gray-400 flex items-start gap-2">
                              <span className="text-blue-400 mt-1">•</span>
                              <span>{evidence}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
