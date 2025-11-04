import { useState, useMemo, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useParams } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/Card';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { apiClient } from '../../lib/api';
import type { LegalTask, AggregationResult, Feedback } from '../../types';
import { toast } from 'sonner';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Sankey,
  LineChart,
  Line,
} from 'recharts';

interface DisagreementMetrics {
  shannon_entropy: number;
  consensus_level: number;
  position_count: number;
  uncertainty_threshold: number;
  preserves_uncertainty: boolean;
}

interface AlternativePosition {
  position: string;
  support_percentage: number;
  authority_weighted_percentage: number;
  reasoning: string[];
  supporters: string[];
}

interface AggregationViewerProps {
  taskId?: number;
  realtime?: boolean;
  showUncertainty?: boolean;
}

export function AggregationViewer({ taskId: propTaskId, realtime = false, showUncertainty = true }: AggregationViewerProps) {
  const { taskId: routeTaskId } = useParams<{ taskId: string }>();
  const taskId = propTaskId || (routeTaskId ? parseInt(routeTaskId, 10) : 0);
  const [viewMode, setViewMode] = useState<'overview' | 'uncertainty' | 'positions' | 'process'>('overview');
  const [selectedPosition, setSelectedPosition] = useState<string | null>(null);

  // Fetch task details
  const { data: task, isLoading: loadingTask } = useQuery({
    queryKey: ['task', taskId],
    queryFn: () => apiClient.tasks.get(taskId),
    refetchInterval: realtime ? 5000 : false,
  });

  // Fetch aggregation result
  const { data: aggregationResult, isLoading: loadingAggregation } = useQuery({
    queryKey: ['aggregation', taskId],
    queryFn: () => apiClient.tasks.getAggregation(taskId),
    refetchInterval: realtime ? 5000 : false,
    enabled: !!task && task.status === 'AGGREGATED',
  });

  // Fetch all feedback for this task with real API data
  const { data: allFeedback, isLoading: loadingFeedback, error: feedbackError } = useQuery({
    queryKey: ['feedback-task', taskId],
    queryFn: async () => {
      try {
        // Get feedback for this task from backend
        const feedback = await apiClient.feedback.getByTask(taskId);
        return feedback;
      } catch (error) {
        console.error('Failed to load task feedback:', error);
        // Return empty array on error
        return [];
      }
    },
    enabled: !!taskId && taskId > 0,
    refetchInterval: realtime ? 5000 : false,
    retry: 2,
    staleTime: realtime ? 0 : 2 * 60 * 1000, // 2 minutes if not realtime
  });

  // Show error toast when feedback fails to load
  useEffect(() => {
    if (feedbackError) {
      toast.error('Failed to load task feedback', {
        description: 'Disagreement metrics may be unavailable.'
      });
    }
  }, [feedbackError]);

  // Calculate disagreement metrics using Shannon entropy
  const disagreementMetrics = useMemo((): DisagreementMetrics => {
    if (!allFeedback || allFeedback.length === 0) {
      return {
        shannon_entropy: 0,
        consensus_level: 0,
        position_count: 0,
        uncertainty_threshold: 0.4,
        preserves_uncertainty: false,
      };
    }

    // Extract positions and their weights
    const positions = new Map<string, number>();
    let totalWeight = 0;

    allFeedback.forEach(feedback => {
      const position = feedback.feedback_data.validated_answer || 'Unknown';
      const weight = feedback.metadata?.authority_weight || 1;
      positions.set(position, (positions.get(position) || 0) + weight);
      totalWeight += weight;
    });

    // Calculate Shannon entropy: δ = -1/log|P| Σ ρ(p)logρ(p)
    let entropy = 0;
    const positionCount = positions.size;
    
    if (positionCount > 1) {
      positions.forEach(weight => {
        const probability = weight / totalWeight;
        if (probability > 0) {
          entropy -= probability * Math.log2(probability);
        }
      });
      entropy = entropy / Math.log2(positionCount); // Normalize
    }

    const uncertaintyThreshold = 0.4;
    const preservesUncertainty = entropy > uncertaintyThreshold;

    return {
      shannon_entropy: entropy,
      consensus_level: 1 - entropy,
      position_count: positionCount,
      uncertainty_threshold: uncertaintyThreshold,
      preserves_uncertainty: preservesUncertainty,
    };
  }, [allFeedback]);

  // Extract alternative positions
  const alternativePositions = useMemo((): AlternativePosition[] => {
    if (!allFeedback || allFeedback.length === 0) return [];

    const positionMap = new Map<string, {
      supporters: string[],
      reasoning: string[],
      totalWeight: number,
      count: number,
    }>();

    let totalWeight = 0;

    allFeedback.forEach(feedback => {
      const position = feedback.feedback_data.validated_answer || 'Unknown';
      const weight = feedback.metadata?.authority_weight || 1;
      const reasoning = feedback.feedback_data.reasoning || 'No reasoning provided';
      const supporter = `User ${feedback.user_id}`;

      totalWeight += weight;

      if (!positionMap.has(position)) {
        positionMap.set(position, {
          supporters: [],
          reasoning: [],
          totalWeight: 0,
          count: 0,
        });
      }

      const posData = positionMap.get(position)!;
      posData.supporters.push(supporter);
      posData.reasoning.push(reasoning);
      posData.totalWeight += weight;
      posData.count += 1;
    });

    return Array.from(positionMap.entries()).map(([position, data]) => ({
      position,
      support_percentage: (data.count / allFeedback.length) * 100,
      authority_weighted_percentage: (data.totalWeight / totalWeight) * 100,
      reasoning: data.reasoning,
      supporters: data.supporters,
    })).sort((a, b) => b.authority_weighted_percentage - a.authority_weighted_percentage);
  }, [allFeedback]);

  // Colors for visualizations
  const COLORS = ['#8B5CF6', '#06D6A0', '#FFB500', '#F72585', '#4CC9F0'];

  if (loadingTask || loadingAggregation || loadingFeedback) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-400"></div>
      </div>
    );
  }

  if (!task) {
    return (
      <Card className="border-red-700">
        <CardContent className="text-center py-12">
          <p className="text-red-400">Task not found</p>
        </CardContent>
      </Card>
    );
  }

  if (task.status !== 'AGGREGATED') {
    return (
      <Card className="border-yellow-700 bg-yellow-950/20">
        <CardContent className="text-center py-12">
          <div className="text-4xl mb-4">⏳</div>
          <h3 className="text-xl font-bold text-yellow-400 mb-2">Aggregation In Progress</h3>
          <p className="text-yellow-200">
            This task is currently in {task.status} status. Aggregation results will be available once evaluation is complete.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <Card className="border-purple-700 bg-gradient-to-r from-purple-950/20 to-blue-950/20">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-3 text-2xl">
                🔮 RLCF Aggregation Analysis
                {realtime && (
                  <Badge variant="outline" className="text-green-400 border-green-400">
                    🔄 Live
                  </Badge>
                )}
              </CardTitle>
              <p className="text-slate-400 mt-1">
                Task #{taskId} • {task.task_type} • Uncertainty-Preserving Aggregation
              </p>
            </div>
            <div className="text-right">
              <div className="text-sm text-slate-400">Disagreement Level (δ)</div>
              <div className="text-4xl font-bold text-purple-400">
                {disagreementMetrics.shannon_entropy.toFixed(3)}
              </div>
              <div className={`text-sm ${disagreementMetrics.preserves_uncertainty ? 'text-yellow-400' : 'text-green-400'}`}>
                {disagreementMetrics.preserves_uncertainty ? 'Uncertainty Preserved' : 'Consensus Reached'}
              </div>
            </div>
          </div>
        </CardHeader>
      </Card>

      {/* View Mode Selector */}
      <div className="flex justify-center space-x-2">
        {(['overview', 'uncertainty', 'positions', 'process'] as const).map((mode) => (
          <Button
            key={mode}
            variant={viewMode === mode ? "default" : "outline"}
            onClick={() => setViewMode(mode)}
            size="sm"
            className="capitalize"
          >
            {mode}
          </Button>
        ))}
      </div>

      {/* Overview Mode */}
      {viewMode === 'overview' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Consensus Gauge */}
          <Card className="border-slate-700">
            <CardHeader>
              <CardTitle>📊 Consensus Level</CardTitle>
              <p className="text-slate-400 text-sm">
                Consensus = 1 - δ, where δ is normalized Shannon entropy
              </p>
            </CardHeader>
            <CardContent>
              <div className="relative">
                <div className="text-center mb-4">
                  <div className="text-4xl font-bold text-purple-400">
                    {(disagreementMetrics.consensus_level * 100).toFixed(1)}%
                  </div>
                  <div className="text-slate-400">Community Consensus</div>
                </div>
                <div className="w-full bg-slate-800 rounded-full h-4 mb-4">
                  <div
                    className={`h-4 rounded-full transition-all duration-500 ${
                      disagreementMetrics.consensus_level > 0.6 
                        ? 'bg-green-500' 
                        : disagreementMetrics.consensus_level > 0.3
                        ? 'bg-yellow-500'
                        : 'bg-red-500'
                    }`}
                    style={{ width: `${disagreementMetrics.consensus_level * 100}%` }}
                  ></div>
                </div>
                <div className="flex justify-between text-xs text-slate-500">
                  <span>High Disagreement</span>
                  <span>Strong Consensus</span>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Position Distribution */}
          <Card className="border-slate-700">
            <CardHeader>
              <CardTitle>🥧 Position Distribution</CardTitle>
              <p className="text-slate-400 text-sm">
                Authority-weighted vs. simple count
              </p>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie
                    data={alternativePositions}
                    cx="50%"
                    cy="50%"
                    outerRadius={100}
                    fill="#8884d8"
                    dataKey="authority_weighted_percentage"
                    label={({ position, authority_weighted_percentage }) => 
                      `${position}: ${authority_weighted_percentage.toFixed(1)}%`
                    }
                  >
                    {alternativePositions.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip 
                    formatter={(value: number) => [`${value.toFixed(1)}%`, 'Authority Weighted']}
                  />
                </PieChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Uncertainty Mode */}
      {viewMode === 'uncertainty' && showUncertainty && (
        <div className="space-y-6">
          {/* Uncertainty Analysis */}
          <Card className="border-slate-700">
            <CardHeader>
              <CardTitle>🌊 Uncertainty Analysis</CardTitle>
              <p className="text-slate-400">
                Formula: δ = -1/log|P| Σ ρ(p)log ρ(p) where P is position set
              </p>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <div className="text-center p-4 bg-slate-800/50 rounded-lg">
                  <div className="text-3xl font-bold text-purple-400">
                    {disagreementMetrics.shannon_entropy.toFixed(3)}
                  </div>
                  <div className="text-slate-400 text-sm">Shannon Entropy (δ)</div>
                </div>
                <div className="text-center p-4 bg-slate-800/50 rounded-lg">
                  <div className="text-3xl font-bold text-blue-400">
                    {disagreementMetrics.position_count}
                  </div>
                  <div className="text-slate-400 text-sm">Distinct Positions (|P|)</div>
                </div>
                <div className="text-center p-4 bg-slate-800/50 rounded-lg">
                  <div className="text-3xl font-bold text-yellow-400">
                    {disagreementMetrics.uncertainty_threshold}
                  </div>
                  <div className="text-slate-400 text-sm">Threshold (τ)</div>
                </div>
              </div>

              {disagreementMetrics.preserves_uncertainty ? (
                <div className="mt-6 p-4 border-2 border-yellow-700 rounded-lg bg-yellow-950/20">
                  <h4 className="text-lg font-semibold text-yellow-400 mb-2">⚠️ Uncertainty Preserved</h4>
                  <p className="text-yellow-200 text-sm mb-3">
                    δ &gt; τ ({disagreementMetrics.shannon_entropy.toFixed(3)} &gt; {disagreementMetrics.uncertainty_threshold})
                  </p>
                  <p className="text-yellow-200 text-sm">
                    The system will output uncertainty-preserving response with alternative positions.
                  </p>
                </div>
              ) : (
                <div className="mt-6 p-4 border-2 border-green-700 rounded-lg bg-green-950/20">
                  <h4 className="text-lg font-semibold text-green-400 mb-2">✅ Consensus Reached</h4>
                  <p className="text-green-200 text-sm mb-3">
                    δ ≤ τ ({disagreementMetrics.shannon_entropy.toFixed(3)} ≤ {disagreementMetrics.uncertainty_threshold})
                  </p>
                  <p className="text-green-200 text-sm">
                    The system will output consensus response with high confidence.
                  </p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Epistemic Metadata */}
          {disagreementMetrics.preserves_uncertainty && (
            <Card className="border-slate-700">
              <CardHeader>
                <CardTitle>🧠 Epistemic Metadata</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div>
                    <h5 className="font-semibold text-slate-200 mb-2">Uncertainty Sources</h5>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                      <div className="p-3 bg-slate-800/50 rounded">
                        <div className="text-sm font-medium text-purple-400">Interpretive Ambiguity</div>
                        <div className="text-xs text-slate-400">Multiple valid legal interpretations exist</div>
                      </div>
                      <div className="p-3 bg-slate-800/50 rounded">
                        <div className="text-sm font-medium text-blue-400">Expert Disagreement</div>
                        <div className="text-xs text-slate-400">Domain experts hold different positions</div>
                      </div>
                    </div>
                  </div>
                  
                  <div>
                    <h5 className="font-semibold text-slate-200 mb-2">Suggested Research Directions</h5>
                    <ul className="text-sm text-slate-400 space-y-1">
                      <li>• Investigate precedent applicability in similar cases</li>
                      <li>• Analyze jurisdictional variations in interpretation</li>
                      <li>• Review recent scholarly commentary on this topic</li>
                    </ul>
                  </div>
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      )}

      {/* Positions Mode */}
      {viewMode === 'positions' && (
        <div className="space-y-6">
          <Card className="border-slate-700">
            <CardHeader>
              <CardTitle>🎭 Alternative Positions</CardTitle>
              <p className="text-slate-400">Authority-weighted community positions</p>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {alternativePositions.map((position, idx) => (
                  <div 
                    key={idx}
                    className={`p-4 rounded-lg border transition-all cursor-pointer ${
                      selectedPosition === position.position
                        ? 'border-purple-700 bg-purple-950/20'
                        : 'border-slate-700 bg-slate-800/30 hover:border-slate-600'
                    }`}
                    onClick={() => setSelectedPosition(
                      selectedPosition === position.position ? null : position.position
                    )}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <h4 className="text-lg font-semibold text-slate-200">
                        {idx === 0 ? '👑' : '🎯'} Position {idx + 1}: {position.position}
                      </h4>
                      <div className="text-right">
                        <div className="text-purple-400 font-semibold">
                          {position.authority_weighted_percentage.toFixed(1)}%
                        </div>
                        <div className="text-xs text-slate-400">
                          Authority Weighted
                        </div>
                      </div>
                    </div>
                    
                    <div className="flex items-center gap-4 mb-3">
                      <div className="flex-1">
                        <div className="text-xs text-slate-400 mb-1">Authority Weight</div>
                        <div className="w-full bg-slate-700 rounded-full h-2">
                          <div
                            className="bg-purple-500 h-2 rounded-full transition-all duration-300"
                            style={{ width: `${position.authority_weighted_percentage}%` }}
                          ></div>
                        </div>
                      </div>
                      <div className="text-xs text-slate-400">
                        {position.supporters.length} supporters
                      </div>
                    </div>

                    {selectedPosition === position.position && (
                      <div className="mt-4 pt-4 border-t border-slate-600">
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                          <div>
                            <h5 className="font-semibold text-slate-300 mb-2">Supporters</h5>
                            <div className="space-y-1">
                              {position.supporters.map((supporter, sidx) => (
                                <Badge key={sidx} variant="outline" className="text-xs">
                                  {supporter}
                                </Badge>
                              ))}
                            </div>
                          </div>
                          <div>
                            <h5 className="font-semibold text-slate-300 mb-2">Key Reasoning</h5>
                            <div className="space-y-2">
                              {position.reasoning.slice(0, 3).map((reason, ridx) => (
                                <p key={ridx} className="text-sm text-slate-400 italic">
                                  "{reason.substring(0, 100)}..."
                                </p>
                              ))}
                            </div>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Process Mode */}
      {viewMode === 'process' && (
        <Card className="border-slate-700">
          <CardHeader>
            <CardTitle>⚙️ Aggregation Process</CardTitle>
            <p className="text-slate-400">RLCF Algorithm Steps</p>
          </CardHeader>
          <CardContent>
            <div className="space-y-6">
              {[
                {
                  step: 1,
                  title: "Feedback Collection",
                  description: "Blind evaluation with authority-weighted scoring",
                  status: "completed",
                  details: `${allFeedback?.length || 0} feedback entries collected`
                },
                {
                  step: 2,
                  title: "Authority Weighting",
                  description: "Apply dynamic authority scores to feedback",
                  status: "completed", 
                  details: "Authority scores applied using A(t) = α·B + β·T(t-1) + γ·P(t)"
                },
                {
                  step: 3,
                  title: "Disagreement Calculation",
                  description: "Shannon entropy-based disagreement quantification",
                  status: "completed",
                  details: `δ = ${disagreementMetrics.shannon_entropy.toFixed(3)}`
                },
                {
                  step: 4,
                  title: "Uncertainty Check",
                  description: `Compare δ against threshold τ = ${disagreementMetrics.uncertainty_threshold}`,
                  status: "completed",
                  details: disagreementMetrics.preserves_uncertainty 
                    ? "δ > τ: Uncertainty preserved"
                    : "δ ≤ τ: Consensus reached"
                },
                {
                  step: 5,
                  title: "Output Generation",
                  description: disagreementMetrics.preserves_uncertainty
                    ? "Uncertainty-preserving output with alternative positions"
                    : "Consensus output with high confidence",
                  status: "completed",
                  details: `${alternativePositions.length} positions identified`
                }
              ].map((step, idx) => (
                <div key={idx} className="flex items-start gap-4">
                  <div className="flex-shrink-0">
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-semibold ${
                      step.status === 'completed' 
                        ? 'bg-green-600 text-white' 
                        : 'bg-slate-600 text-slate-300'
                    }`}>
                      {step.step}
                    </div>
                  </div>
                  <div className="flex-1">
                    <h4 className="font-semibold text-slate-200">{step.title}</h4>
                    <p className="text-sm text-slate-400 mb-1">{step.description}</p>
                    <p className="text-xs text-purple-400">{step.details}</p>
                  </div>
                  <div className="flex-shrink-0">
                    {step.status === 'completed' && (
                      <Badge className="bg-green-600">✓ Done</Badge>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}