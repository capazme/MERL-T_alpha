/**
 * Pipeline Metrics Card
 *
 * Displays per-stage performance metrics for the orchestration pipeline.
 * Shows execution time, success rate, and throughput for each stage.
 */

import { Card, CardContent, CardHeader, CardTitle } from '@components/ui/Card';
import { Progress } from '@components/ui/Progress';
import { Badge } from '@components/ui/Badge';
import { Clock, Zap, TrendingUp, Activity } from 'lucide-react';

interface StageMetric {
  stage_name: string;
  avg_time_ms: number;
  p95_time_ms?: number;
  success_rate?: number;
  icon: React.ReactNode;
  color: string;
}

interface PipelineMetricsCardProps {
  stageTimings?: Record<string, number>; // From execution trace
  totalTimeMs?: number;
}

const stageConfig: Record<string, { icon: React.ReactNode; color: string; label: string }> = {
  preprocessing: {
    icon: <Activity className="w-4 h-4" />,
    color: 'text-blue-400',
    label: 'Preprocessing',
  },
  routing: {
    icon: <TrendingUp className="w-4 h-4" />,
    color: 'text-purple-400',
    label: 'Routing',
  },
  retrieval: {
    icon: <Zap className="w-4 h-4" />,
    color: 'text-yellow-400',
    label: 'Retrieval',
  },
  reasoning: {
    icon: <Activity className="w-4 h-4" />,
    color: 'text-green-400',
    label: 'Reasoning',
  },
  synthesis: {
    icon: <Clock className="w-4 h-4" />,
    color: 'text-orange-400',
    label: 'Synthesis',
  },
};

export function PipelineMetricsCard({ stageTimings, totalTimeMs }: PipelineMetricsCardProps) {
  if (!stageTimings || Object.keys(stageTimings).length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Clock className="w-5 h-5" />
            Pipeline Performance
          </CardTitle>
        </CardHeader>
        <CardContent className="py-8 text-center text-gray-400">
          <p>Stage timing data not available for this query.</p>
        </CardContent>
      </Card>
    );
  }

  const stages = Object.entries(stageTimings).map(([stageName, timeMs]) => {
    const config = stageConfig[stageName] || {
      icon: <Activity className="w-4 h-4" />,
      color: 'text-gray-400',
      label: stageName.replace(/_/g, ' '),
    };

    const percentage = totalTimeMs ? (timeMs / totalTimeMs) * 100 : 0;

    return {
      stage_name: stageName,
      avg_time_ms: timeMs,
      percentage,
      ...config,
    };
  });

  // Sort by time descending
  stages.sort((a, b) => b.avg_time_ms - a.avg_time_ms);

  const getPerformanceColor = (timeMs: number) => {
    if (timeMs < 500) return 'text-green-400';
    if (timeMs < 2000) return 'text-yellow-400';
    return 'text-red-400';
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Clock className="w-5 h-5" />
          Pipeline Performance
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Total Time Summary */}
        {totalTimeMs && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 pb-4 border-b border-gray-700">
            <div className="bg-gray-800 p-4 rounded-lg">
              <div className="text-sm text-gray-400 mb-1">Total Time</div>
              <div className={`text-2xl font-semibold ${getPerformanceColor(totalTimeMs)}`}>
                {totalTimeMs.toFixed(0)}ms
              </div>
            </div>
            <div className="bg-gray-800 p-4 rounded-lg">
              <div className="text-sm text-gray-400 mb-1">Stages</div>
              <div className="text-2xl font-semibold text-white">{stages.length}</div>
            </div>
            <div className="bg-gray-800 p-4 rounded-lg">
              <div className="text-sm text-gray-400 mb-1">Slowest Stage</div>
              <div className="text-lg font-semibold text-white capitalize">
                {stages[0]?.stage_name.replace(/_/g, ' ')}
              </div>
            </div>
            <div className="bg-gray-800 p-4 rounded-lg">
              <div className="text-sm text-gray-400 mb-1">Fastest Stage</div>
              <div className="text-lg font-semibold text-white capitalize">
                {stages[stages.length - 1]?.stage_name.replace(/_/g, ' ')}
              </div>
            </div>
          </div>
        )}

        {/* Stage Breakdown */}
        <div className="space-y-4">
          <h4 className="text-sm font-medium text-gray-400">Stage Breakdown</h4>
          {stages.map((stage) => (
            <div key={stage.stage_name} className="space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className={stage.color}>{stage.icon}</div>
                  <span className="text-white font-medium capitalize">{stage.label}</span>
                </div>
                <div className="flex items-center gap-3">
                  <Badge variant="outline" className="font-mono">
                    {stage.avg_time_ms.toFixed(0)}ms
                  </Badge>
                  <span className="text-sm text-gray-400 w-12 text-right">
                    {stage.percentage.toFixed(1)}%
                  </span>
                </div>
              </div>
              <Progress value={stage.percentage} className="h-2" />
            </div>
          ))}
        </div>

        {/* Performance Analysis */}
        <div className="pt-4 border-t border-gray-700">
          <h4 className="text-sm font-medium text-gray-400 mb-3">Performance Analysis</h4>
          <div className="space-y-2 text-sm">
            {totalTimeMs && totalTimeMs < 5000 && (
              <div className="flex items-start gap-2 text-green-400">
                <span className="mt-0.5">✓</span>
                <span>Query executed efficiently under 5 seconds target.</span>
              </div>
            )}
            {totalTimeMs && totalTimeMs >= 5000 && totalTimeMs < 10000 && (
              <div className="flex items-start gap-2 text-yellow-400">
                <span className="mt-0.5">⚠</span>
                <span>Query execution time above 5s target. Consider optimization.</span>
              </div>
            )}
            {totalTimeMs && totalTimeMs >= 10000 && (
              <div className="flex items-start gap-2 text-red-400">
                <span className="mt-0.5">!</span>
                <span>
                  Query execution time significantly above target. Review bottlenecks in{' '}
                  {stages[0]?.stage_name.replace(/_/g, ' ')} stage.
                </span>
              </div>
            )}

            {stages[0] && stages[0].percentage > 50 && (
              <div className="flex items-start gap-2 text-orange-400">
                <span className="mt-0.5">⚠</span>
                <span>
                  {stages[0].label} stage accounts for {stages[0].percentage.toFixed(0)}% of total time.
                  This may indicate a bottleneck.
                </span>
              </div>
            )}

            {stages.every((s) => s.percentage < 35) && (
              <div className="flex items-start gap-2 text-green-400">
                <span className="mt-0.5">✓</span>
                <span>Well-balanced pipeline with no single bottleneck stage.</span>
              </div>
            )}
          </div>
        </div>

        {/* Future Metrics Placeholder */}
        <div className="pt-4 border-t border-gray-700">
          <div className="p-4 bg-blue-500/10 border border-blue-500/30 rounded-lg">
            <p className="text-sm text-blue-300">
              <strong>Coming Soon:</strong> P95 latency, success rate per stage, throughput metrics,
              and historical comparison charts.
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
