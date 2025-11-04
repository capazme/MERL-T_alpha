import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import { Card, CardContent, CardHeader, CardTitle } from '@components/ui/Card';
import { useSystemMetrics, useLeaderboard, useTaskDistribution } from '@hooks/useApi';
import { Users, ClipboardCheck, TrendingUp, AlertTriangle, Award } from 'lucide-react';
import { QueryWrapper } from '@components/shared/QueryWrapper';

const COLORS = ['#8884d8', '#82ca9d', '#ffc658', '#ff8042', '#0088FE', '#00C49F', '#FFBB28'];

export function Analytics() {
  const systemMetricsQuery = useSystemMetrics();
  const leaderboardQuery = useLeaderboard(5);
  const taskDistributionQuery = useTaskDistribution();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-white mb-2">Analytics Dashboard</h1>
        <p className="text-slate-400">System performance and community insights</p>
      </div>

      <QueryWrapper query={systemMetricsQuery} loadingMessage="Loading system metrics...">
        {(metrics) => (
          <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium text-slate-400">Total Users</CardTitle>
                <Users className="h-4 w-4 text-blue-400" />
              </CardHeader>
              <CardContent><div className="text-2xl font-bold text-white">{metrics.totalUsers}</div></CardContent>
            </Card>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium text-slate-400">Total Tasks</CardTitle>
                <ClipboardCheck className="h-4 w-4 text-violet-400" />
              </CardHeader>
              <CardContent><div className="text-2xl font-bold text-white">{metrics.totalTasks}</div></CardContent>
            </Card>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium text-slate-400">Active Evaluations</CardTitle>
                <AlertTriangle className="h-4 w-4 text-orange-400" />
              </CardHeader>
              <CardContent><div className="text-2xl font-bold text-white">{metrics.activeEvaluations}</div></CardContent>
            </Card>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium text-slate-400">Avg. Consensus</CardTitle>
                <TrendingUp className="h-4 w-4 text-green-400" />
              </CardHeader>
              <CardContent><div className="text-2xl font-bold text-white">{(metrics.averageConsensus * 100).toFixed(1)}%</div></CardContent>
            </Card>
            <Card>
              <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                <CardTitle className="text-sm font-medium text-slate-400">Completion Rate</CardTitle>
                <ClipboardCheck className="h-4 w-4 text-pink-400" />
              </CardHeader>
              <CardContent><div className="text-2xl font-bold text-white">{(metrics.completionRate * 100).toFixed(1)}%</div></CardContent>
            </Card>
          </div>
        )}
      </QueryWrapper>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        <div className="lg:col-span-3">
          <Card>
            <CardHeader><CardTitle>Task Type Distribution</CardTitle></CardHeader>
            <CardContent>
              <QueryWrapper query={taskDistributionQuery} minHeight="300px">
                {(data) => {
                  const chartData = Object.entries(data).map(([name, value]) => ({ name, value }));
                  return (
                    <ResponsiveContainer width="100%" height={300}>
                      <PieChart>
                        <Pie data={chartData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={100} fill="#8884d8" label>
                          {chartData.map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                          ))}
                        </Pie>
                        <Tooltip />
                        <Legend />
                      </PieChart>
                    </ResponsiveContainer>
                  );
                }}
              </QueryWrapper>
            </CardContent>
          </Card>
        </div>
        <div className="lg:col-span-2">
          <Card>
            <CardHeader><CardTitle>Leaderboard</CardTitle></CardHeader>
            <CardContent>
              <QueryWrapper query={leaderboardQuery} minHeight="300px">
                {(users) => (
                  <ul className="space-y-3">
                    {users.map((user, index) => (
                      <li key={user.id} className="flex items-center justify-between p-2 rounded-lg bg-slate-800/50">
                        <div className="flex items-center gap-3">
                          <span className="text-lg font-bold text-slate-500">{index + 1}</span>
                          <span className="font-medium text-white">{user.username}</span>
                        </div>
                        <div className="flex items-center gap-2 text-violet-400">
                          <Award className="h-4 w-4" />
                          <span className="font-mono text-sm">{user.authority_score.toFixed(3)}</span>
                        </div>
                      </li>
                    ))}
                  </ul>
                )}
              </QueryWrapper>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}