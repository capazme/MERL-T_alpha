import React, { useState, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { Badge } from '../../components/ui/Badge';
import { apiClient } from '../../lib/api';
import { 
  RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, Radar, 
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  LineChart, Line, ScatterChart, Scatter, Cell, PieChart, Pie
} from 'recharts';
import type { BiasReport, BiasMetrics, BiasAnalysis } from '../../types';

interface BiasAnalysisDashboardProps {
  taskId?: number;
  userId?: number;
  timeRange?: 'week' | 'month' | 'quarter' | 'year';
}

interface BiasDetectionResult {
  dimension: string;
  severity: number;
  confidence: number;
  description: string;
  examples: string[];
  mitigation: string[];
}

interface BiasCorrelation {
  factor1: string;
  factor2: string;
  correlation: number;
  significance: number;
}

const BIAS_DIMENSIONS = [
  { key: 'demographic', label: 'Demographic', color: '#FF6B6B', description: 'Age, gender, ethnicity correlations' },
  { key: 'professional', label: 'Professional', color: '#4ECDC4', description: 'Career, education, experience clustering' },
  { key: 'temporal', label: 'Temporal', color: '#45B7D1', description: 'Time-based drift patterns' },
  { key: 'geographic', label: 'Geographic', color: '#96CEB4', description: 'Regional or jurisdictional clustering' },
  { key: 'cognitive', label: 'Cognitive', color: '#FECA57', description: 'Thinking style and approach biases' },
  { key: 'confirmation', label: 'Confirmation', color: '#FF9FF3', description: 'Prior belief reinforcement' }
];

const SEVERITY_LEVELS = [
  { min: 0, max: 0.2, level: 'Minimal', color: '#10B981', action: 'Monitor' },
  { min: 0.2, max: 0.4, level: 'Low', color: '#84CC16', action: 'Track' },
  { min: 0.4, max: 0.6, level: 'Moderate', color: '#F59E0B', action: 'Investigate' },
  { min: 0.6, max: 0.8, level: 'High', color: '#EF4444', action: 'Mitigate' },
  { min: 0.8, max: 1.0, level: 'Critical', color: '#DC2626', action: 'Immediate Action' }
];

const MITIGATION_STRATEGIES = {
  demographic: [
    'Implement demographic-blind evaluation protocols',
    'Increase diversity in evaluation panels',
    'Use stratified sampling for feedback collection',
    'Apply inverse propensity weighting'
  ],
  professional: [
    'Cross-domain expert recruitment',
    'Rotate evaluation assignments across expertise areas',
    'Weight adjustments for professional clustering',
    'Anonymous peer review processes'
  ],
  temporal: [
    'Time-aware authority score adjustments',
    'Seasonal evaluation pattern analysis',
    'Rolling window normalization',
    'Drift detection algorithms'
  ],
  geographic: [
    'Multi-jurisdictional validation panels',
    'Regional legal expertise mapping',
    'Weighted geographic representation',
    'Cross-border expert exchange programs'
  ],
  cognitive: [
    'Devil\'s advocate assignment protocols',
    'Structured argumentation frameworks',
    'Cognitive diversity metrics',
    'Perspective-taking exercises'
  ],
  confirmation: [
    'Blind evaluation procedures',
    'Evidence-first reasoning protocols',
    'Alternative hypothesis testing',
    'Pre-commitment to evaluation criteria'
  ]
};

export function BiasAnalysisDashboard({ taskId, userId, timeRange = 'month' }: BiasAnalysisDashboardProps) {
  const [selectedDimension, setSelectedDimension] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<'overview' | 'detailed' | 'mitigation' | 'trends'>('overview');
  const [severityFilter, setSeverityFilter] = useState<string>('all');

  // Fetch bias analysis data
  const { data: biasAnalysis, isLoading: loadingBias } = useQuery({
    queryKey: ['bias-analysis', taskId, userId, timeRange],
    queryFn: () => apiClient.analytics.getBiasAnalysis({ taskId, userId, timeRange }),
    refetchInterval: 30000 // Update every 30 seconds
  });

  // Fetch bias correlations
  const { data: biasCorrelations } = useQuery({
    queryKey: ['bias-correlations', taskId, userId, timeRange],
    queryFn: () => apiClient.analytics.getBiasCorrelations({ taskId, userId, timeRange })
  });

  // Calculate overall bias score using RLCF formula: Btotal = √Σbi²
  const overallBiasScore = useMemo(() => {
    if (!biasAnalysis || !biasAnalysis.dimensions) return 0;
    
    const sumOfSquares = BIAS_DIMENSIONS.reduce((sum, dim) => {
      const score = biasAnalysis.dimensions[dim.key] || 0;
      return sum + Math.pow(score, 2);
    }, 0);
    
    return Math.sqrt(sumOfSquares);
  }, [biasAnalysis]);

  // Format radar chart data
  const radarData = useMemo(() => {
    if (!biasAnalysis) return [];
    
    return BIAS_DIMENSIONS.map(dim => ({
      dimension: dim.label,
      bias: biasAnalysis.dimensions?.[dim.key] || 0,
      threshold: 0.6,
      fullMark: 1.0
    }));
  }, [biasAnalysis]);

  // Get severity level for overall score
  const getSeverityLevel = (score: number) => {
    return SEVERITY_LEVELS.find(level => score >= level.min && score < level.max) || SEVERITY_LEVELS[0];
  };

  // Filter bias detections by severity
  const filteredDetections = useMemo(() => {
    if (!biasAnalysis?.detections) return [];
    
    return biasAnalysis.detections.filter((detection: BiasDetectionResult) => {
      if (severityFilter === 'all') return true;
      const level = getSeverityLevel(detection.severity);
      return level.level.toLowerCase() === severityFilter;
    });
  }, [biasAnalysis, severityFilter]);

  const currentSeverityLevel = getSeverityLevel(overallBiasScore);

  if (loadingBias) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-400"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <Card className={`border-2 ${overallBiasScore > 0.6 ? 'border-red-600 bg-red-950/10' : overallBiasScore > 0.3 ? 'border-yellow-600 bg-yellow-950/10' : 'border-green-600 bg-green-950/10'}`}>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-3 text-2xl">
                <span className="text-3xl">🔍</span>
                RLCF Bias Analysis
                <Badge 
                  style={{ backgroundColor: currentSeverityLevel.color }}
                  className="text-white"
                >
                  {currentSeverityLevel.level}
                </Badge>
              </CardTitle>
              <p className="text-slate-400 mt-1">
                Multi-dimensional bias detection • Btotal = √Σbi² • {taskId ? `Task #${taskId}` : userId ? `User #${userId}` : 'System-wide'}
              </p>
            </div>
            <div className="text-right">
              <div className="text-sm text-slate-400">Overall Bias Score</div>
              <div className="text-4xl font-bold" style={{ color: currentSeverityLevel.color }}>
                {overallBiasScore.toFixed(3)}
              </div>
              <div className="text-sm" style={{ color: currentSeverityLevel.color }}>
                {currentSeverityLevel.action}
              </div>
            </div>
          </div>
        </CardHeader>
      </Card>

      {/* View Mode Selector */}
      <div className="flex justify-center space-x-2">
        {(['overview', 'detailed', 'mitigation', 'trends'] as const).map((mode) => (
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
          {/* 6D Bias Radar Chart */}
          <Card className="border-slate-700">
            <CardHeader>
              <CardTitle>🎯 6-Dimensional Bias Radar</CardTitle>
              <p className="text-slate-400">
                Comprehensive bias assessment across all RLCF dimensions
              </p>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={350}>
                <RadarChart data={radarData}>
                  <PolarGrid stroke="#374151" />
                  <PolarAngleAxis 
                    dataKey="dimension" 
                    tick={{ fill: '#9CA3AF', fontSize: 12 }}
                  />
                  <PolarRadiusAxis 
                    domain={[0, 1]} 
                    tick={{ fill: '#6B7280', fontSize: 10 }}
                    angle={30}
                  />
                  <Radar
                    name="Bias Level"
                    dataKey="bias"
                    stroke="#EF4444"
                    fill="#EF4444"
                    fillOpacity={0.3}
                    strokeWidth={2}
                  />
                  <Radar
                    name="Threshold"
                    dataKey="threshold"
                    stroke="#F59E0B"
                    strokeDasharray="5 5"
                    strokeWidth={1}
                    fillOpacity={0}
                  />
                  <Tooltip 
                    contentStyle={{ 
                      backgroundColor: '#1F2937', 
                      border: '1px solid #374151',
                      borderRadius: '8px'
                    }}
                    formatter={(value: number, name: string) => [
                      value.toFixed(3),
                      name === 'bias' ? 'Bias Score' : 'Critical Threshold'
                    ]}
                  />
                </RadarChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          {/* Bias Distribution */}
          <Card className="border-slate-700">
            <CardHeader>
              <CardTitle>📊 Bias Score Distribution</CardTitle>
              <p className="text-slate-400">Individual dimension breakdown</p>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {BIAS_DIMENSIONS.map((dim, idx) => {
                  const score = biasAnalysis?.dimensions?.[dim.key] || 0;
                  const severity = getSeverityLevel(score);
                  
                  return (
                    <div 
                      key={dim.key}
                      className={`p-3 rounded-lg border cursor-pointer transition-all ${
                        selectedDimension === dim.key
                          ? 'border-purple-500 bg-purple-950/20'
                          : 'border-slate-700 hover:border-slate-600'
                      }`}
                      onClick={() => setSelectedDimension(
                        selectedDimension === dim.key ? null : dim.key
                      )}
                    >
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-2">
                          <div 
                            className="w-3 h-3 rounded-full"
                            style={{ backgroundColor: dim.color }}
                          />
                          <span className="font-medium text-slate-200">{dim.label}</span>
                          <Badge 
                            style={{ backgroundColor: severity.color }}
                            className="text-white text-xs"
                          >
                            {severity.level}
                          </Badge>
                        </div>
                        <span className="font-mono text-sm">{score.toFixed(3)}</span>
                      </div>
                      <div className="w-full bg-slate-700 rounded-full h-2 mb-2">
                        <div
                          className="h-2 rounded-full transition-all duration-300"
                          style={{ 
                            width: `${score * 100}%`,
                            backgroundColor: severity.color 
                          }}
                        />
                      </div>
                      <p className="text-xs text-slate-400">{dim.description}</p>
                      
                      {selectedDimension === dim.key && (
                        <div className="mt-3 pt-3 border-t border-slate-600">
                          <h5 className="text-sm font-semibold text-slate-300 mb-2">Recommended Actions:</h5>
                          <ul className="text-xs text-slate-400 space-y-1">
                            {MITIGATION_STRATEGIES[dim.key as keyof typeof MITIGATION_STRATEGIES]?.slice(0, 2).map((strategy, sidx) => (
                              <li key={sidx}>• {strategy}</li>
                            ))}
                          </ul>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Detailed Analysis Mode */}
      {viewMode === 'detailed' && (
        <div className="space-y-6">
          {/* Severity Filter */}
          <Card className="border-slate-700">
            <CardHeader>
              <CardTitle>🔧 Filter by Severity</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex flex-wrap gap-2">
                <Button
                  variant={severityFilter === 'all' ? 'default' : 'outline'}
                  onClick={() => setSeverityFilter('all')}
                  size="sm"
                >
                  All ({biasAnalysis?.detections?.length || 0})
                </Button>
                {SEVERITY_LEVELS.map(level => {
                  const count = biasAnalysis?.detections?.filter((d: BiasDetectionResult) => 
                    getSeverityLevel(d.severity).level === level.level
                  ).length || 0;
                  
                  return (
                    <Button
                      key={level.level}
                      variant={severityFilter === level.level.toLowerCase() ? 'default' : 'outline'}
                      onClick={() => setSeverityFilter(level.level.toLowerCase())}
                      size="sm"
                      style={{ 
                        borderColor: count > 0 ? level.color : undefined,
                        color: severityFilter === level.level.toLowerCase() ? 'white' : level.color
                      }}
                    >
                      {level.level} ({count})
                    </Button>
                  );
                })}
              </div>
            </CardContent>
          </Card>

          {/* Detailed Detections */}
          <div className="grid grid-cols-1 gap-4">
            {filteredDetections.map((detection: BiasDetectionResult, idx: number) => {
              const severity = getSeverityLevel(detection.severity);
              
              return (
                <Card key={idx} className={`border-l-4`} style={{ borderLeftColor: severity.color }}>
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <CardTitle className="flex items-center gap-3">
                        <span className="capitalize">{detection.dimension}</span> Bias Detection
                        <Badge style={{ backgroundColor: severity.color }} className="text-white">
                          {severity.level}
                        </Badge>
                      </CardTitle>
                      <div className="text-right">
                        <div className="text-lg font-bold" style={{ color: severity.color }}>
                          {detection.severity.toFixed(3)}
                        </div>
                        <div className="text-xs text-slate-400">
                          {(detection.confidence * 100).toFixed(1)}% confidence
                        </div>
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <p className="text-slate-300 mb-4">{detection.description}</p>
                    
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <h4 className="font-semibold text-slate-200 mb-2">Examples</h4>
                        <ul className="text-sm text-slate-400 space-y-1">
                          {detection.examples.map((example, eidx) => (
                            <li key={eidx} className="italic">"{example}"</li>
                          ))}
                        </ul>
                      </div>
                      <div>
                        <h4 className="font-semibold text-slate-200 mb-2">Mitigation Steps</h4>
                        <ul className="text-sm text-slate-400 space-y-1">
                          {detection.mitigation.map((step, midx) => (
                            <li key={midx}>• {step}</li>
                          ))}
                        </ul>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </div>
      )}

      {/* Mitigation Mode */}
      {viewMode === 'mitigation' && (
        <div className="space-y-6">
          <Card className="border-slate-700">
            <CardHeader>
              <CardTitle>🛡️ Bias Mitigation Strategies</CardTitle>
              <p className="text-slate-400">Comprehensive mitigation framework for each bias dimension</p>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {BIAS_DIMENSIONS.map(dim => {
                  const score = biasAnalysis?.dimensions?.[dim.key] || 0;
                  const severity = getSeverityLevel(score);
                  const strategies = MITIGATION_STRATEGIES[dim.key as keyof typeof MITIGATION_STRATEGIES];
                  
                  return (
                    <div key={dim.key} className="p-4 rounded-lg border border-slate-700">
                      <div className="flex items-center gap-3 mb-3">
                        <div 
                          className="w-4 h-4 rounded-full"
                          style={{ backgroundColor: dim.color }}
                        />
                        <h4 className="font-semibold text-slate-200">{dim.label} Bias</h4>
                        <Badge style={{ backgroundColor: severity.color }} className="text-white text-xs">
                          {score.toFixed(3)}
                        </Badge>
                      </div>
                      
                      <div className="space-y-2">
                        {strategies?.map((strategy, sidx) => (
                          <div key={sidx} className="flex items-start gap-2 text-sm">
                            <div className="text-purple-400 mt-1">•</div>
                            <span className="text-slate-300">{strategy}</span>
                          </div>
                        ))}
                      </div>
                      
                      <div className="mt-3 pt-3 border-t border-slate-600">
                        <div className="text-xs text-slate-400">
                          Priority: <span style={{ color: severity.color }}>{severity.action}</span>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Trends Mode */}
      {viewMode === 'trends' && biasAnalysis?.timeline && (
        <div className="space-y-6">
          <Card className="border-slate-700">
            <CardHeader>
              <CardTitle>📈 Bias Trend Analysis</CardTitle>
              <p className="text-slate-400">Temporal evolution of bias scores</p>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={400}>
                <LineChart data={biasAnalysis.timeline}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                  <XAxis 
                    dataKey="timestamp" 
                    stroke="#9CA3AF"
                    tickFormatter={(value) => new Date(value).toLocaleDateString()}
                  />
                  <YAxis stroke="#9CA3AF" domain={[0, 1]} />
                  <Tooltip 
                    contentStyle={{ 
                      backgroundColor: '#1F2937', 
                      border: '1px solid #374151',
                      borderRadius: '8px'
                    }}
                    labelFormatter={(value) => new Date(value).toLocaleDateString()}
                  />
                  {BIAS_DIMENSIONS.map(dim => (
                    <Line
                      key={dim.key}
                      type="monotone"
                      dataKey={dim.key}
                      stroke={dim.color}
                      strokeWidth={2}
                      name={dim.label}
                      connectNulls={false}
                    />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>

          {/* Bias Correlations */}
          {biasCorrelations && (
            <Card className="border-slate-700">
              <CardHeader>
                <CardTitle>🔗 Bias Correlations</CardTitle>
                <p className="text-slate-400">Statistical relationships between bias dimensions</p>
              </CardHeader>
              <CardContent>
                <ResponsiveContainer width="100%" height={300}>
                  <ScatterChart data={biasCorrelations}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                    <XAxis 
                      dataKey="correlation" 
                      domain={[-1, 1]}
                      stroke="#9CA3AF"
                      name="Correlation"
                    />
                    <YAxis 
                      dataKey="significance" 
                      domain={[0, 1]}
                      stroke="#9CA3AF"
                      name="Significance"
                    />
                    <Tooltip 
                      contentStyle={{ 
                        backgroundColor: '#1F2937', 
                        border: '1px solid #374151',
                        borderRadius: '8px'
                      }}
                      formatter={(value, name) => [typeof value === 'number' ? value.toFixed(3) : value, name]}
                      labelFormatter={(_, payload) => 
                        payload?.[0] ? `${payload[0].payload.factor1} ↔ ${payload[0].payload.factor2}` : ''
                      }
                    />
                    <Scatter 
                      dataKey="significance" 
                      fill="#8B5CF6"
                      stroke="#8B5CF6"
                      strokeWidth={1}
                    />
                  </ScatterChart>
                </ResponsiveContainer>
              </CardContent>
            </Card>
          )}
        </div>
      )}
    </div>
  );
}