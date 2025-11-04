import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/Card';
import { Badge } from '../../components/ui/Badge';
import { Button } from '../../components/ui/Button';
import { apiClient } from '../../lib/api';
import { useAuthStore } from '../../app/store/auth';

interface LeaderboardEntry {
  rank: number;
  user_id: number;
  username: string;
  authority_score: number;
  tasks_completed: number;
  recent_performance: number;
  percentile: number;
}

export function Leaderboard() {
  const { user } = useAuthStore();
  const [timeframe, setTimeframe] = useState<'all' | '30d' | '7d'>('all');
  const [limit, setLimit] = useState(50);

  const { data: leaderboard, isLoading } = useQuery({
    queryKey: ['leaderboard', timeframe, limit],
    queryFn: async () => {
      const users = await apiClient.analytics.getLeaderboard(limit);
      return users.map((user, index) => ({
        rank: index + 1,
        user_id: user.id,
        username: user.username,
        authority_score: user.authority_score,
        tasks_completed: user.tasks_completed || 0,
        recent_performance: user.recent_performance || 0,
        percentile: Math.max(1, Math.round(((users.length - index) / users.length) * 100)),
      })) as LeaderboardEntry[];
    },
  });

  const currentUserRank = leaderboard?.find(entry => entry.user_id === user?.id);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-purple-400"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">🏆 RLCF Leaderboard</h1>
          <p className="text-slate-400">Authority rankings based on dynamic scoring model</p>
        </div>
        <div className="flex gap-2">
          {(['all', '30d', '7d'] as const).map((period) => (
            <Button
              key={period}
              variant={timeframe === period ? 'default' : 'outline'}
              size="sm"
              onClick={() => setTimeframe(period)}
            >
              {period.toUpperCase()}
            </Button>
          ))}
        </div>
      </div>

      {/* Current User Rank Card */}
      {currentUserRank && (
        <Card className="border-purple-700 bg-purple-950/20">
          <CardContent className="flex items-center justify-between p-6">
            <div className="flex items-center gap-4">
              <div className="text-4xl font-bold text-purple-400">
                #{currentUserRank.rank}
              </div>
              <div>
                <div className="text-xl font-semibold text-white">
                  Your Rank: {currentUserRank.username}
                </div>
                <div className="text-slate-400">
                  {currentUserRank.percentile}th percentile
                </div>
              </div>
            </div>
            <div className="text-right">
              <div className="text-2xl font-bold text-purple-400">
                {currentUserRank.authority_score.toFixed(3)}
              </div>
              <div className="text-sm text-slate-400">
                {currentUserRank.tasks_completed} tasks
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Leaderboard Table */}
      <Card className="border-slate-700">
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>Authority Rankings</CardTitle>
            <div className="text-sm text-slate-400">
              Formula: A(t) = α·B + β·T(t-1) + γ·P(t)
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-2">
            {leaderboard?.map((entry) => {
              const isCurrentUser = entry.user_id === user?.id;
              const isTopTen = entry.rank <= 10;
              const medalEmoji = entry.rank === 1 ? '🥇' : entry.rank === 2 ? '🥈' : entry.rank === 3 ? '🥉' : '';
              
              return (
                <div 
                  key={entry.user_id}
                  className={`flex items-center justify-between p-4 rounded-lg transition-all ${
                    isCurrentUser 
                      ? 'bg-purple-950/30 border-2 border-purple-700' 
                      : isTopTen
                      ? 'bg-slate-800/50 border border-slate-600'
                      : 'bg-slate-800/30 hover:bg-slate-800/40'
                  }`}
                >
                  <div className="flex items-center gap-4">
                    <div className="flex items-center gap-2 min-w-[60px]">
                      <span className="text-lg font-bold text-slate-400">
                        #{entry.rank}
                      </span>
                      {medalEmoji && <span className="text-xl">{medalEmoji}</span>}
                    </div>
                    <div>
                      <div className={`font-semibold ${
                        isCurrentUser ? 'text-purple-400' : 'text-slate-200'
                      }`}>
                        {entry.username}
                        {isCurrentUser && (
                          <Badge className="ml-2 bg-purple-600">You</Badge>
                        )}
                      </div>
                      <div className="text-sm text-slate-400">
                        {entry.tasks_completed} tasks • {entry.percentile}th percentile
                      </div>
                    </div>
                  </div>
                  
                  <div className="flex items-center gap-6">
                    <div className="text-right">
                      <div className="text-lg font-bold text-purple-400">
                        {entry.authority_score.toFixed(3)}
                      </div>
                      <div className="text-xs text-slate-500">
                        Authority Score
                      </div>
                    </div>
                    
                    {/* Authority breakdown visualization */}
                    <div className="flex items-center gap-1">
                      <div className="w-2 h-8 bg-blue-500 rounded-sm" 
                           title={`Baseline: ${(entry.authority_score * 0.3).toFixed(3)}`} />
                      <div className="w-2 h-8 bg-green-500 rounded-sm" 
                           title={`Track Record: ${(entry.authority_score * 0.5).toFixed(3)}`} />
                      <div className="w-2 h-8 bg-yellow-500 rounded-sm" 
                           title={`Recent: ${(entry.authority_score * 0.2).toFixed(3)}`} />
                    </div>
                  </div>
                </div>
              );
            }) || (
              <div className="text-center py-12">
                <p className="text-slate-500">No leaderboard data available</p>
              </div>
            )}
          </div>
          
          {/* Load More */}
          {leaderboard && leaderboard.length >= limit && (
            <div className="text-center mt-6">
              <Button 
                variant="outline" 
                onClick={() => setLimit(prev => prev + 25)}
              >
                Load More Rankings
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
      
      {/* Legend */}
      <Card className="border-slate-700">
        <CardContent className="p-4">
          <div className="flex items-center justify-between text-sm">
            <div className="flex items-center gap-4">
              <span className="text-slate-400">Authority Components:</span>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 bg-blue-500 rounded"></div>
                <span className="text-slate-300">Credentials (30%)</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 bg-green-500 rounded"></div>
                <span className="text-slate-300">Track Record (50%)</span>
              </div>
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 bg-yellow-500 rounded"></div>
                <span className="text-slate-300">Recent Performance (20%)</span>
              </div>
            </div>
            <div className="text-slate-500">
              Updated every evaluation cycle
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}