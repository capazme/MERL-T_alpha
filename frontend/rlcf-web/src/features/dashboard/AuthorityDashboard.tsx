import { useState, useMemo, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/Card';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { apiClient } from '../../lib/api';
import { useAuthStore } from '../../app/store/auth';
import { toast } from 'sonner';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
} from 'recharts';

interface AuthorityBreakdown {
  baseline_credentials: number;
  track_record: number;
  recent_performance: number;
  total_score: number;
  percentile_rank: number;
}

interface AuthorityHistory {
  timestamp: string;
  score: number;
  reason: string;
  task_type?: string;
}

interface PeerComparison {
  user_id: number;
  username: string;
  authority_score: number;
  rank: number;
  tasks_completed: number;
}

export function AuthorityDashboard() {
  const { user } = useAuthStore();
  const [timeRange, setTimeRange] = useState<'7d' | '30d' | '90d' | '1y'>('30d');
  const [selectedMetric, setSelectedMetric] = useState<'authority' | 'tasks' | 'accuracy'>('authority');

  // Fetch user's authority breakdown with real data from backend
  const { data: authorityBreakdown, isLoading: loadingBreakdown } = useQuery({
    queryKey: ['authority-breakdown', user?.id, timeRange],
    queryFn: async () => {
      if (!user) return null;
      try {
        // Get authority breakdown from backend API
        const response = await apiClient.users.getAuthorityData(user.id, timeRange);
        return {
          baseline_credentials: response.baseline_credentials || user.baseline_credential_score || 0,
          track_record: response.track_record || user.track_record_score || 0,
          recent_performance: response.recent_performance || (user.recent_performance || 0),
          total_score: response.total_score || user.authority_score,
          percentile_rank: response.percentile_rank || 50,
        } as AuthorityBreakdown;
      } catch (error) {
        console.error('Failed to load authority data, using fallback:', error);
        // Fallback to calculating from current user data
        return {
          baseline_credentials: user.baseline_credential_score || user.authority_score * 0.3,
          track_record: user.track_record_score || user.authority_score * 0.5,
          recent_performance: user.recent_performance || user.authority_score * 0.2,
          total_score: user.authority_score,
          percentile_rank: 50,
        } as AuthorityBreakdown;
      }
    },
    enabled: !!user,
    retry: 2,
  });

  // Fetch authority evolution history with real data from backend
  const { data: authorityHistory, isLoading: loadingHistory, error: historyError } = useQuery({
    queryKey: ['authority-history', user?.id, timeRange],
    queryFn: async () => {
      if (!user) return [];
      try {
        // Get authority history from backend API
        const response = await apiClient.users.getAuthorityHistory(user.id, timeRange);
        return response.history || [];
      } catch (error) {
        console.error('Failed to load authority history:', error);
        // Return empty array if API fails
        return [];
      }
    },
    enabled: !!user,
    retry: 2,
    staleTime: 2 * 60 * 1000, // 2 minutes
  });

  // Fetch peer comparison data with user context
  const { data: peerComparison, isLoading: loadingPeers, error: peersError } = useQuery({
    queryKey: ['peer-comparison', user?.id],
    queryFn: async () => {
      if (!user) return [];
      try {
        // Get leaderboard with top 20 users
        const leaderboard = await apiClient.analytics.getLeaderboard(20);

        // Ensure current user is in the list
        const userInList = leaderboard.find(u => u.id === user.id);
        if (!userInList && leaderboard.length > 0) {
          // Add current user if not in top 20
          leaderboard.push(user);
        }

        return leaderboard.map((u, index) => ({
          user_id: u.id,
          username: u.username,
          authority_score: u.authority_score,
          rank: index + 1,
          tasks_completed: u.tasks_completed || 0,
        })) as PeerComparison[];
      } catch (error) {
        console.error('Failed to load peer comparison:', error);
        return [];
      }
    },
    enabled: !!user,
    retry: 2,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  // Show error toasts when queries fail
  useEffect(() => {
    if (historyError) {
      toast.error('Failed to load authority history', {
        description: 'Some data may be unavailable. Please refresh the page.'
      });
    }
  }, [historyError]);

  useEffect(() => {
    if (peersError) {
      toast.error('Failed to load peer comparison', {
        description: 'Leaderboard data could not be loaded.'
      });
    }
  }, [peersError]);

  // RLCF formula components for radar chart
  const radarData = useMemo(() => {
    if (!authorityBreakdown) return [];
    return [
      {
        component: 'Baseline Credentials',
        value: authorityBreakdown.baseline_credentials,
        fullMark: 1.0,
        formula: 'α = 0.3'
      },
      {
        component: 'Track Record',
        value: authorityBreakdown.track_record,
        fullMark: 1.0,
        formula: 'β = 0.5'
      },
      {
        component: 'Recent Performance',
        value: authorityBreakdown.recent_performance,
        fullMark: 1.0,
        formula: 'γ = 0.2'
      },
    ];
  }, [authorityBreakdown]);

  // Achievement system
  const achievements = useMemo(() => {
    if (!user || !authorityBreakdown) return [];
    
    const achievements = [];
    if (authorityBreakdown.total_score >= 0.8) {
      achievements.push({ 
        icon: '🏆', 
        title: 'Expert Authority', 
        description: 'Authority score ≥ 0.8',
        color: 'text-yellow-400'
      });
    }
    if (authorityBreakdown.percentile_rank >= 90) {
      achievements.push({ 
        icon: '⭐', 
        title: 'Top 10%', 
        description: 'Top percentile performer',
        color: 'text-purple-400'
      });
    }
    if (user.tasks_completed && user.tasks_completed >= 50) {
      achievements.push({ 
        icon: '💎', 
        title: 'Dedicated Evaluator', 
        description: '50+ tasks completed',
        color: 'text-blue-400'
      });
    }
    return achievements;
  }, [user, authorityBreakdown]);

  if (!user) {
    return (
      <Card className="border-red-700">
        <CardContent className="text-center py-12">
          <p className="text-red-400">Please log in to view your authority dashboard.</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header Card */}
      <Card className="border-purple-700 bg-gradient-to-r from-purple-950/20 to-blue-950/20">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-3 text-2xl">
                ⚖️ Authority Dashboard
                <Badge variant="outline" className="text-purple-400 border-purple-400">
                  RLCF Framework
                </Badge>
              </CardTitle>
              <p className="text-slate-400 mt-1">
                Dynamic Authority Scoring: A(t) = α·B + β·T(t-1) + γ·P(t)
              </p>
            </div>
            <div className="text-right">
              <div className="text-sm text-slate-400">Current Authority</div>
              <div className="text-4xl font-bold text-purple-400">
                {user.authority_score.toFixed(3)}
              </div>
              <div className="text-sm text-slate-400">
                Rank: #{authorityBreakdown?.percentile_rank || '—'}th percentile
              </div>
            </div>
          </div>
        </CardHeader>
      </Card>

      {/* Time Range Selector */}
      <div className="flex justify-center space-x-2">
        {(['7d', '30d', '90d', '1y'] as const).map((range) => (
          <Button
            key={range}
            variant={timeRange === range ? "default" : "outline"}
            onClick={() => setTimeRange(range)}
            size="sm"
          >
            {range.toUpperCase()}
          </Button>
        ))}
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
        {/* Authority Evolution Chart */}
        <Card className="border-slate-700">
          <CardHeader>
            <CardTitle>📈 Authority Evolution</CardTitle>
            <p className="text-slate-400 text-sm">
              Track record component: T(t) = λ·T(t-1) + (1-λ)·Q(t), where λ = 0.95
            </p>
          </CardHeader>
          <CardContent>
            {loadingHistory ? (
              <div className="h-64 flex items-center justify-center">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-400"></div>
              </div>
            ) : authorityHistory && authorityHistory.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={authorityHistory}>
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
                      border: '1px solid #6366F1',
                      borderRadius: '8px'
                    }}
                    formatter={(value: number) => [value.toFixed(3), 'Authority Score']}
                    labelFormatter={(value) => new Date(value).toLocaleDateString()}
                  />
                  <Legend />
                  <Line
                    type="monotone"
                    dataKey="score"
                    stroke="#8B5CF6"
                    strokeWidth={3}
                    dot={{ fill: '#8B5CF6', strokeWidth: 2, r: 4 }}
                    name="Authority Score"
                  />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="h-64 flex flex-col items-center justify-center text-center p-6">
                <div className="text-4xl mb-3">📊</div>
                <p className="text-slate-400 mb-2">No authority history available yet</p>
                <p className="text-sm text-slate-500">
                  Complete more tasks to see your authority score evolution over time
                </p>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Authority Components Breakdown (Radar) */}
        <Card className="border-slate-700">
          <CardHeader>
            <CardTitle>🎯 RLCF Components Breakdown</CardTitle>
            <p className="text-slate-400 text-sm">
              Mathematical decomposition of your authority score
            </p>
          </CardHeader>
          <CardContent>
            {loadingBreakdown ? (
              <div className="h-64 flex items-center justify-center">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-400"></div>
              </div>
            ) : (
              <ResponsiveContainer width="100%" height={300}>
                <RadarChart data={radarData}>
                  <PolarGrid stroke="#374151" />
                  <PolarAngleAxis 
                    dataKey="component" 
                    tick={{ fontSize: 12, fill: '#9CA3AF' }}
                  />
                  <PolarRadiusAxis 
                    angle={90} 
                    domain={[0, 1]} 
                    tick={{ fontSize: 10, fill: '#6B7280' }}
                  />
                  <Radar
                    name="Score"
                    dataKey="value"
                    stroke="#8B5CF6"
                    fill="#8B5CF6"
                    fillOpacity={0.3}
                    strokeWidth={2}
                  />
                  <Tooltip 
                    contentStyle={{ 
                      backgroundColor: '#1F2937', 
                      border: '1px solid #6366F1',
                      borderRadius: '8px'
                    }}
                    formatter={(value: number, name, props) => [
                      value.toFixed(3), 
                      `${props.payload?.formula} = ${value.toFixed(3)}`
                    ]}
                  />
                </RadarChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Achievements */}
        <Card className="border-slate-700">
          <CardHeader>
            <CardTitle>🏆 Achievements</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {achievements.length > 0 ? (
                achievements.map((achievement, idx) => (
                  <div key={idx} className="flex items-center gap-3 p-3 bg-slate-800/50 rounded-lg">
                    <span className="text-2xl">{achievement.icon}</span>
                    <div>
                      <div className={`font-semibold ${achievement.color}`}>
                        {achievement.title}
                      </div>
                      <div className="text-sm text-slate-400">
                        {achievement.description}
                      </div>
                    </div>
                  </div>
                ))
              ) : (
                <p className="text-slate-500 text-center py-4">
                  Complete more evaluations to unlock achievements
                </p>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Quick Stats */}
        <Card className="border-slate-700">
          <CardHeader>
            <CardTitle>📊 Quick Stats</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="flex justify-between items-center">
                <span className="text-slate-400">Tasks Completed</span>
                <span className="font-semibold text-blue-400">{user.tasks_completed || 0}</span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-slate-400">Authority Percentile</span>
                <span className="font-semibold text-purple-400">
                  {authorityBreakdown?.percentile_rank || 0}th
                </span>
              </div>
              <div className="flex justify-between items-center">
                <span className="text-slate-400">Total Score</span>
                <span className="font-semibold text-green-400">
                  {authorityBreakdown?.total_score.toFixed(3) || '0.000'}
                </span>
              </div>
              <div className="border-t border-slate-600 pt-2">
                <div className="text-xs text-slate-500 space-y-1">
                  <p>• Baseline: {(authorityBreakdown?.baseline_credentials || 0).toFixed(3)}</p>
                  <p>• Track Record: {(authorityBreakdown?.track_record || 0).toFixed(3)}</p>
                  <p>• Recent: {(authorityBreakdown?.recent_performance || 0).toFixed(3)}</p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Authority Simulator */}
        <Card className="border-slate-700">
          <CardHeader>
            <CardTitle>🔮 Authority Simulator</CardTitle>
            <p className="text-slate-400 text-sm">What-if analysis</p>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div>
                <label className="text-sm text-slate-400">Next Task Quality Score</label>
                <input 
                  type="range" 
                  min="0" 
                  max="10" 
                  step="0.1"
                  className="w-full mt-1"
                  onChange={(e) => {
                    const quality = parseFloat(e.target.value);
                    // Simulate new authority score
                    if (authorityBreakdown) {
                      const newRecent = quality / 10;
                      const newTotal = authorityBreakdown.baseline_credentials + 
                                     authorityBreakdown.track_record * 0.95 + 
                                     newRecent * 0.05; // λ = 0.95, (1-λ) = 0.05
                      e.target.nextElementSibling!.textContent = 
                        `Projected: ${newTotal.toFixed(3)} (${quality}/10)`;
                    }
                  }}
                />
                <div className="text-xs text-slate-400 mt-1">
                  Projected: {user.authority_score.toFixed(3)}
                </div>
              </div>
              
              <div className="pt-2 border-t border-slate-600">
                <p className="text-xs text-slate-500">
                  Formula: A(t) = 0.3·B + 0.5·T(t-1) + 0.2·P(t)
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Peer Comparison */}
      <Card className="border-slate-700">
        <CardHeader>
          <CardTitle>👥 Peer Comparison</CardTitle>
          <p className="text-slate-400">Community leaderboard and your position</p>
        </CardHeader>
        <CardContent>
          {loadingPeers ? (
            <div className="h-32 flex items-center justify-center">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-400"></div>
            </div>
          ) : (
            <div className="space-y-2 max-h-64 overflow-y-auto">
              {peerComparison?.map((peer, idx) => (
                <div 
                  key={peer.user_id}
                  className={`flex items-center justify-between p-3 rounded-lg ${
                    peer.user_id === user.id 
                      ? 'bg-purple-950/30 border border-purple-700' 
                      : 'bg-slate-800/30'
                  }`}
                >
                  <div className="flex items-center gap-3">
                    <div className="text-sm font-mono text-slate-400">
                      #{peer.rank}
                    </div>
                    <div>
                      <div className={`font-semibold ${
                        peer.user_id === user.id ? 'text-purple-400' : 'text-slate-200'
                      }`}>
                        {peer.username} {peer.user_id === user.id && '(You)'}
                      </div>
                      <div className="text-xs text-slate-500">
                        {peer.tasks_completed} tasks completed
                      </div>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="font-semibold text-purple-400">
                      {peer.authority_score.toFixed(3)}
                    </div>
                  </div>
                </div>
              )) || (
                <p className="text-center text-slate-500 py-8">
                  No peer data available
                </p>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}