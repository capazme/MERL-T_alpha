/**
 * ConfidenceScoreChart - Histogram of confidence scores
 *
 * Visualizes distribution of confidence scores across staging entities.
 * Helps identify quality patterns and set appropriate thresholds.
 */

import React, { useMemo } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';

// =============================================================================
// Types
// =============================================================================

interface StagingEntity {
  id: number;
  confidence_score: number;
  source_type: string;
}

interface ConfidenceScoreChartProps {
  entities: StagingEntity[];
}

// =============================================================================
// Helper Functions
// =============================================================================

const calculateDistribution = (entities: StagingEntity[]) => {
  // Bins: 0-0.25, 0.25-0.5, 0.5-0.75, 0.75-0.9, 0.9-0.95, 0.95-1.0
  const bins = [
    { label: '0-25%', min: 0, max: 0.25, count: 0, color: 'bg-red-500' },
    { label: '25-50%', min: 0.25, max: 0.5, count: 0, color: 'bg-orange-500' },
    { label: '50-75%', min: 0.5, max: 0.75, count: 0, color: 'bg-yellow-500' },
    { label: '75-90%', min: 0.75, max: 0.9, count: 0, color: 'bg-lime-500' },
    { label: '90-95%', min: 0.9, max: 0.95, count: 0, color: 'bg-green-500' },
    { label: '95-100%', min: 0.95, max: 1.0, count: 0, color: 'bg-emerald-600' },
  ];

  entities.forEach((entity) => {
    const score = entity.confidence_score;
    const bin = bins.find((b) => score >= b.min && score < b.max) || bins[bins.length - 1];
    bin.count++;
  });

  return bins;
};

const calculateStats = (entities: StagingEntity[]) => {
  if (entities.length === 0) return { mean: 0, median: 0, min: 0, max: 0 };

  const scores = entities.map((e) => e.confidence_score).sort((a, b) => a - b);
  const sum = scores.reduce((acc, val) => acc + val, 0);

  return {
    mean: sum / scores.length,
    median: scores[Math.floor(scores.length / 2)],
    min: scores[0],
    max: scores[scores.length - 1],
  };
};

const calculateBySource = (entities: StagingEntity[]) => {
  const sourceStats: Record<string, { count: number; avgConfidence: number }> = {};

  entities.forEach((entity) => {
    if (!sourceStats[entity.source_type]) {
      sourceStats[entity.source_type] = { count: 0, avgConfidence: 0 };
    }
    sourceStats[entity.source_type].count++;
    sourceStats[entity.source_type].avgConfidence += entity.confidence_score;
  });

  // Calculate averages
  Object.keys(sourceStats).forEach((source) => {
    sourceStats[source].avgConfidence /= sourceStats[source].count;
  });

  return sourceStats;
};

// =============================================================================
// Main Component
// =============================================================================

export const ConfidenceScoreChart: React.FC<ConfidenceScoreChartProps> = ({ entities }) => {
  const distribution = useMemo(() => calculateDistribution(entities), [entities]);
  const stats = useMemo(() => calculateStats(entities), [entities]);
  const bySource = useMemo(() => calculateBySource(entities), [entities]);

  const maxCount = Math.max(...distribution.map((b) => b.count));

  return (
    <Card>
      <CardHeader>
        <CardTitle>Confidence Score Distribution</CardTitle>
      </CardHeader>
      <CardContent>
        {/* Histogram */}
        <div className="space-y-2 mb-6">
          {distribution.map((bin, idx) => (
            <div key={idx} className="flex items-center gap-3">
              <div className="w-20 text-sm font-medium text-gray-700">{bin.label}</div>
              <div className="flex-1 bg-gray-100 rounded-full h-8 relative overflow-hidden">
                <div
                  className={`${bin.color} h-full transition-all duration-500 flex items-center justify-end pr-3`}
                  style={{
                    width: maxCount > 0 ? `${(bin.count / maxCount) * 100}%` : '0%',
                  }}
                >
                  {bin.count > 0 && (
                    <span className="text-white font-semibold text-sm">{bin.count}</span>
                  )}
                </div>
              </div>
              <div className="w-16 text-sm text-gray-600 text-right">
                {maxCount > 0 ? ((bin.count / entities.length) * 100).toFixed(1) : 0}%
              </div>
            </div>
          ))}
        </div>

        {/* Statistics */}
        <div className="grid grid-cols-4 gap-4 pb-4 mb-4 border-b">
          <div className="text-center">
            <div className="text-2xl font-bold text-blue-600">{(stats.mean * 100).toFixed(1)}%</div>
            <div className="text-xs text-gray-600">Mean</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-purple-600">
              {(stats.median * 100).toFixed(1)}%
            </div>
            <div className="text-xs text-gray-600">Median</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-red-600">{(stats.min * 100).toFixed(1)}%</div>
            <div className="text-xs text-gray-600">Min</div>
          </div>
          <div className="text-center">
            <div className="text-2xl font-bold text-green-600">
              {(stats.max * 100).toFixed(1)}%
            </div>
            <div className="text-xs text-gray-600">Max</div>
          </div>
        </div>

        {/* By Source */}
        <div>
          <h4 className="font-semibold text-gray-900 mb-3">Confidence by Source</h4>
          <div className="grid grid-cols-2 gap-3">
            {Object.entries(bySource).map(([source, data]) => (
              <div key={source} className="bg-gray-50 rounded-lg p-3">
                <div className="flex justify-between items-center mb-1">
                  <Badge variant="outline">{source}</Badge>
                  <span className="text-sm font-medium text-gray-600">{data.count} entities</span>
                </div>
                <div className="text-lg font-bold text-gray-900">
                  {(data.avgConfidence * 100).toFixed(1)}%
                </div>
                <div className="text-xs text-gray-500">Average Confidence</div>
              </div>
            ))}
          </div>
        </div>

        {/* Quality Recommendations */}
        <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
          <h5 className="font-semibold text-blue-900 text-sm mb-1">💡 Quality Recommendations</h5>
          <ul className="text-xs text-blue-800 space-y-1">
            {stats.mean < 0.75 && (
              <li>• Mean confidence below 75% - consider reviewing extraction quality</li>
            )}
            {distribution[0].count + distribution[1].count > entities.length * 0.2 && (
              <li>• Over 20% entities below 50% confidence - check data source quality</li>
            )}
            {distribution[5].count > entities.length * 0.8 && (
              <li>
                • Over 80% entities above 95% confidence - can increase auto-approval threshold
              </li>
            )}
            {stats.min < 0.5 && (
              <li>• Some very low confidence entities detected - manual review strongly recommended</li>
            )}
          </ul>
        </div>
      </CardContent>
    </Card>
  );
};
