import React, { useState, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { Badge } from '../../components/ui/Badge';
import { apiClient } from '../../lib/api';
import { toast } from 'sonner';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import type { LegalTask, User, TaskAssignment, AssignmentCriteria } from '../../types';

interface TaskAssignmentSystemProps {
  autoAssign?: boolean;
}

interface AssignmentRule {
  id: string;
  name: string;
  description: string;
  criteria: AssignmentCriteria;
  active: boolean;
  priority: number;
}

interface AssignmentStrategy {
  id: string;
  name: string;
  description: string;
  algorithm: 'random' | 'authority_weighted' | 'expertise_based' | 'load_balanced' | 'bias_minimizing';
  parameters: Record<string, any>;
}

const ASSIGNMENT_STRATEGIES: AssignmentStrategy[] = [
  {
    id: 'random',
    name: 'Random Assignment',
    description: 'Purely random selection from eligible evaluators',
    algorithm: 'random',
    parameters: {}
  },
  {
    id: 'authority_weighted',
    name: 'Authority-Weighted Selection',
    description: 'Higher probability for evaluators with higher authority scores',
    algorithm: 'authority_weighted',
    parameters: { min_authority: 0.3, weight_curve: 'linear' }
  },
  {
    id: 'expertise_based',
    name: 'Expertise-Based Matching',
    description: 'Match evaluators to tasks based on domain expertise',
    algorithm: 'expertise_based',
    parameters: { domain_weight: 0.7, experience_weight: 0.3 }
  },
  {
    id: 'load_balanced',
    name: 'Load-Balanced Distribution',
    description: 'Distribute tasks evenly across available evaluators',
    algorithm: 'load_balanced',
    parameters: { max_concurrent_tasks: 5, workload_factor: 0.8 }
  },
  {
    id: 'bias_minimizing',
    name: 'Bias-Minimizing Selection',
    description: 'Select evaluators to minimize potential bias in results',
    algorithm: 'bias_minimizing',
    parameters: { diversity_target: 0.8, demographic_weight: 0.4 }
  }
];

const DEVILS_ADVOCATE_CONFIG = {
  probability: 0.1, // P(advocate) = min(0.1, 3/|E|)
  min_evaluators: 3,
  selection_method: 'random',
  task_specific_prompts: true
};

const COLORS = ['#8B5CF6', '#06D6A0', '#FFB500', '#F72585', '#4CC9F0'];

export function TaskAssignmentSystem({ autoAssign = false }: TaskAssignmentSystemProps) {
  const [selectedStrategy, setSelectedStrategy] = useState<string>('authority_weighted');
  const [assignmentRules, setAssignmentRules] = useState<AssignmentRule[]>([]);
  const [showAdvancedSettings, setShowAdvancedSettings] = useState(false);
  const [batchAssignmentMode, setBatchAssignmentMode] = useState(false);
  const [showBatchConfirmation, setShowBatchConfirmation] = useState(false);

  const queryClient = useQueryClient();

  // Fetch pending tasks for assignment
  const { data: pendingTasks, isLoading: loadingTasks } = useQuery({
    queryKey: ['pending-tasks'],
    queryFn: () => apiClient.tasks.getPendingAssignments(),
    refetchInterval: autoAssign ? 5000 : 30000
  });

  // Fetch available evaluators
  const { data: evaluators, isLoading: loadingEvaluators } = useQuery({
    queryKey: ['available-evaluators'],
    queryFn: () => apiClient.users.getAvailableEvaluators(),
    refetchInterval: 30000
  });

  // Fetch assignment statistics
  const { data: assignmentStats } = useQuery({
    queryKey: ['assignment-stats'],
    queryFn: () => apiClient.admin.getAssignmentStatistics()
  });

  // Assignment mutation
  const assignmentMutation = useMutation({
    mutationFn: (assignment: { taskIds: number[], strategy: string, criteria?: AssignmentCriteria }) =>
      apiClient.admin.assignTasks(assignment),
    onMutate: (variables) => {
      const taskCount = variables.taskIds.length;
      toast.loading(
        taskCount === 1
          ? 'Assigning task to evaluator...'
          : `Assigning ${taskCount} tasks to evaluators...`,
        { id: 'task-assignment' }
      );
    },
    onSuccess: (data, variables) => {
      const taskCount = variables.taskIds.length;
      const assignedCount = data?.assigned_count || taskCount;

      queryClient.invalidateQueries({ queryKey: ['pending-tasks'] });
      queryClient.invalidateQueries({ queryKey: ['assignment-stats'] });

      toast.success(
        taskCount === 1
          ? 'Task assigned successfully! ✅'
          : `${assignedCount} tasks assigned successfully! ✅`,
        {
          id: 'task-assignment',
          description: taskCount === 1
            ? 'The evaluator has been notified.'
            : `Distributed across ${data?.evaluators_assigned || 'multiple'} evaluators using ${getStrategyDetails(variables.strategy).name}.`
        }
      );

      setShowBatchConfirmation(false);
    },
    onError: (error: any, variables) => {
      const taskCount = variables.taskIds.length;

      toast.error('Task assignment failed', {
        id: 'task-assignment',
        description: error.message || `Failed to assign ${taskCount === 1 ? 'task' : 'tasks'}. Please try again.`
      });

      setShowBatchConfirmation(false);
    }
  });

  // Calculate Devil's Advocate probability
  const calculateDevilsAdvocateProbability = (evaluatorCount: number): number => {
    return Math.min(DEVILS_ADVOCATE_CONFIG.probability, 3 / evaluatorCount);
  };

  // Get strategy details
  const getStrategyDetails = (strategyId: string) => {
    return ASSIGNMENT_STRATEGIES.find(s => s.id === strategyId) || ASSIGNMENT_STRATEGIES[0];
  };

  // Format assignment statistics for charts
  const assignmentDistribution = useMemo(() => {
    if (!assignmentStats) return [];
    
    return assignmentStats.by_evaluator.map((stat: any) => ({
      evaluator: stat.username,
      assigned: stat.assigned_count,
      completed: stat.completed_count,
      authority: stat.authority_score
    }));
  }, [assignmentStats]);

  const taskTypeDistribution = useMemo(() => {
    if (!assignmentStats) return [];
    
    return assignmentStats.by_task_type.map((stat: any) => ({
      type: stat.task_type,
      count: stat.count
    }));
  }, [assignmentStats]);

  // Handle single task assignment
  const handleSingleAssignment = (taskId: number) => {
    const strategy = getStrategyDetails(selectedStrategy);
    assignmentMutation.mutate({
      taskIds: [taskId],
      strategy: strategy.algorithm
    });
  };

  // Handle batch assignment (show confirmation first)
  const handleBatchAssignmentClick = () => {
    if (!pendingTasks || pendingTasks.length === 0) {
      toast.error('No pending tasks to assign');
      return;
    }
    setShowBatchConfirmation(true);
  };

  // Confirm and execute batch assignment
  const confirmBatchAssignment = () => {
    if (!pendingTasks) return;

    const taskIds = pendingTasks.map((task: LegalTask) => task.id);
    const strategy = getStrategyDetails(selectedStrategy);

    assignmentMutation.mutate({
      taskIds,
      strategy: strategy.algorithm,
      criteria: {
        min_authority: strategy.parameters.min_authority || 0,
        max_concurrent: strategy.parameters.max_concurrent_tasks || 5,
        require_expertise: strategy.algorithm === 'expertise_based',
        enable_devils_advocate: true
      }
    });
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">🎯 Task Assignment System</h1>
          <p className="text-slate-400">
            Intelligent task distribution with bias minimization and expertise matching
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Badge variant="outline" className="text-green-400 border-green-400">
            {pendingTasks?.length || 0} Pending
          </Badge>
          <Badge variant="outline" className="text-blue-400 border-blue-400">
            {evaluators?.length || 0} Available
          </Badge>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        {/* Assignment Configuration */}
        <div className="xl:col-span-2 space-y-6">
          {/* Strategy Selection */}
          <Card className="border-slate-700">
            <CardHeader>
              <CardTitle>🧠 Assignment Strategy</CardTitle>
              <p className="text-slate-400">Choose the algorithm for task-evaluator matching</p>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {ASSIGNMENT_STRATEGIES.map((strategy) => (
                  <div
                    key={strategy.id}
                    className={`p-4 rounded-lg border cursor-pointer transition-all ${
                      selectedStrategy === strategy.id
                        ? 'border-purple-500 bg-purple-950/20'
                        : 'border-slate-700 hover:border-slate-600'
                    }`}
                    onClick={() => setSelectedStrategy(strategy.id)}
                  >
                    <h4 className="font-semibold text-slate-200 mb-2">{strategy.name}</h4>
                    <p className="text-sm text-slate-400 mb-3">{strategy.description}</p>
                    
                    {Object.keys(strategy.parameters).length > 0 && (
                      <div className="text-xs text-slate-500">
                        <strong>Parameters:</strong>
                        <ul className="mt-1 space-y-0.5">
                          {Object.entries(strategy.parameters).map(([key, value]) => (
                            <li key={key}>• {key}: {String(value)}</li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Devil's Advocate Configuration */}
          <Card className="border-slate-700">
            <CardHeader>
              <CardTitle>👹 Devil's Advocate System</CardTitle>
              <p className="text-slate-400">
                Automatic assignment for constructive criticism
              </p>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <h4 className="font-semibold text-slate-200 mb-3">Configuration</h4>
                  <div className="space-y-3">
                    <div className="flex justify-between">
                      <span className="text-slate-400">Base Probability</span>
                      <span className="font-mono text-purple-400">{DEVILS_ADVOCATE_CONFIG.probability}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-400">Min Evaluators</span>
                      <span className="font-mono text-blue-400">{DEVILS_ADVOCATE_CONFIG.min_evaluators}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-slate-400">Selection Method</span>
                      <span className="font-mono text-green-400 capitalize">
                        {DEVILS_ADVOCATE_CONFIG.selection_method}
                      </span>
                    </div>
                  </div>
                </div>
                
                <div>
                  <h4 className="font-semibold text-slate-200 mb-3">Formula</h4>
                  <div className="p-3 bg-slate-800/50 rounded font-mono text-sm">
                    <div className="text-purple-400">P(advocate) = min(0.1, 3/|E|)</div>
                    <div className="text-slate-400 text-xs mt-1">
                      where |E| = number of evaluators
                    </div>
                  </div>
                  
                  {evaluators && (
                    <div className="mt-3 text-sm text-slate-400">
                      Current probability: <span className="text-yellow-400 font-mono">
                        {calculateDevilsAdvocateProbability(evaluators.length).toFixed(3)}
                      </span>
                    </div>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Pending Tasks */}
          <Card className="border-slate-700">
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle>📋 Pending Task Assignments</CardTitle>
                <div className="flex gap-2">
                  <Button
                    variant="outline"
                    onClick={() => setBatchAssignmentMode(!batchAssignmentMode)}
                    size="sm"
                  >
                    {batchAssignmentMode ? 'Single Mode' : 'Batch Mode'}
                  </Button>
                  {batchAssignmentMode && (
                    <Button
                      onClick={handleBatchAssignmentClick}
                      disabled={!pendingTasks?.length || assignmentMutation.isPending}
                      className="bg-purple-600 hover:bg-purple-700"
                      size="sm"
                    >
                      {assignmentMutation.isPending ? 'Assigning...' : `Assign All (${pendingTasks?.length || 0})`}
                    </Button>
                  )}
                </div>
              </div>
            </CardHeader>
            <CardContent>
              {loadingTasks ? (
                <div className="flex items-center justify-center h-32">
                  <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-purple-400"></div>
                </div>
              ) : pendingTasks?.length ? (
                <div className="space-y-3 max-h-96 overflow-y-auto">
                  {pendingTasks.map((task: LegalTask) => (
                    <div key={task.id} className="p-4 bg-slate-800/30 rounded-lg">
                      <div className="flex items-center justify-between mb-2">
                        <div className="flex items-center gap-3">
                          <Badge variant="outline" className="text-blue-400 border-blue-400">
                            #{task.id}
                          </Badge>
                          <Badge variant="outline">
                            {task.task_type}
                          </Badge>
                        </div>
                        <div className="text-xs text-slate-400">
                          Created {new Date(task.created_at).toLocaleDateString()}
                        </div>
                      </div>
                      
                      <p className="text-sm text-slate-300 mb-3 line-clamp-2">
                        {task.description || Object.values(task.input_data)[0]?.toString().substring(0, 100)}...
                      </p>
                      
                      {!batchAssignmentMode && (
                        <div className="flex justify-end">
                          <Button
                            onClick={() => handleSingleAssignment(task.id)}
                            disabled={assignmentMutation.isPending}
                            size="sm"
                            className="bg-purple-600 hover:bg-purple-700"
                          >
                            Assign
                          </Button>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-8 text-slate-500">
                  No pending tasks for assignment
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Statistics Sidebar */}
        <div className="space-y-6">
          {/* Quick Stats */}
          <Card className="border-slate-700">
            <CardHeader>
              <CardTitle>📊 Assignment Statistics</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-3">
                <div className="text-center p-3 bg-slate-800/50 rounded">
                  <div className="text-xl font-bold text-blue-400">
                    {assignmentStats?.total_assigned || 0}
                  </div>
                  <div className="text-xs text-slate-400">Total Assigned</div>
                </div>
                <div className="text-center p-3 bg-slate-800/50 rounded">
                  <div className="text-xl font-bold text-green-400">
                    {assignmentStats?.total_completed || 0}
                  </div>
                  <div className="text-xs text-slate-400">Completed</div>
                </div>
                <div className="text-center p-3 bg-slate-800/50 rounded">
                  <div className="text-xl font-bold text-purple-400">
                    {assignmentStats?.avg_completion_time || 0}h
                  </div>
                  <div className="text-xs text-slate-400">Avg Time</div>
                </div>
                <div className="text-center p-3 bg-slate-800/50 rounded">
                  <div className="text-xl font-bold text-yellow-400">
                    {(assignmentStats?.devils_advocate_rate * 100 || 0).toFixed(1)}%
                  </div>
                  <div className="text-xs text-slate-400">Devil's Advocate</div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Available Evaluators */}
          <Card className="border-slate-700">
            <CardHeader>
              <CardTitle>👥 Available Evaluators</CardTitle>
            </CardHeader>
            <CardContent>
              {loadingEvaluators ? (
                <div className="flex items-center justify-center h-24">
                  <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-purple-400"></div>
                </div>
              ) : (
                <div className="space-y-2 max-h-48 overflow-y-auto">
                  {evaluators?.slice(0, 10).map((evaluator: User) => (
                    <div key={evaluator.id} className="flex items-center justify-between p-2 bg-slate-800/30 rounded">
                      <div>
                        <div className="font-medium text-slate-200 text-sm">
                          {evaluator.username}
                        </div>
                        <div className="text-xs text-slate-400">
                          {evaluator.tasks_completed || 0} tasks completed
                        </div>
                      </div>
                      <div className="text-right">
                        <div className="text-sm font-mono text-purple-400">
                          {evaluator.authority_score.toFixed(3)}
                        </div>
                        <div className="text-xs text-slate-500">authority</div>
                      </div>
                    </div>
                  ))}
                  {evaluators && evaluators.length > 10 && (
                    <div className="text-center text-xs text-slate-500 pt-2">
                      +{evaluators.length - 10} more evaluators
                    </div>
                  )}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Task Type Distribution */}
          <Card className="border-slate-700">
            <CardHeader>
              <CardTitle>📈 Task Distribution</CardTitle>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={200}>
                <PieChart>
                  <Pie
                    data={taskTypeDistribution}
                    cx="50%"
                    cy="50%"
                    outerRadius={70}
                    fill="#8884d8"
                    dataKey="count"
                    label={({ type, percent }: any) => `${type}: ${(percent ? percent * 100 : 0).toFixed(0)}%`}
                    labelLine={false}
                  >
                    {taskTypeDistribution.map((entry: any, index: number) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Assignment History */}
      <Card className="border-slate-700">
        <CardHeader>
          <CardTitle>📈 Assignment Performance</CardTitle>
          <p className="text-slate-400">Evaluator workload and completion rates</p>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={assignmentDistribution}>
              <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
              <XAxis 
                dataKey="evaluator" 
                stroke="#9CA3AF" 
                fontSize={12}
                angle={-45}
                textAnchor="end"
                height={60}
              />
              <YAxis stroke="#9CA3AF" fontSize={12} />
              <Tooltip 
                contentStyle={{ 
                  backgroundColor: '#1F2937', 
                  border: '1px solid #374151',
                  borderRadius: '8px'
                }}
              />
              <Bar dataKey="assigned" fill="#8B5CF6" name="Assigned" />
              <Bar dataKey="completed" fill="#10B981" name="Completed" />
            </BarChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      {/* Batch Assignment Confirmation Modal */}
      {showBatchConfirmation && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-50">
          <Card className="max-w-md w-full border-purple-600 bg-slate-900">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-purple-400">
                ⚠️ Confirm Batch Assignment
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="text-slate-300">
                You are about to assign <strong className="text-purple-400">{pendingTasks?.length || 0} tasks</strong> to evaluators using the <strong className="text-blue-400">{getStrategyDetails(selectedStrategy).name}</strong> strategy.
              </p>

              <div className="p-3 bg-purple-950/20 border border-purple-700 rounded-lg space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-slate-400">Strategy:</span>
                  <span className="text-purple-300 font-medium">{getStrategyDetails(selectedStrategy).name}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-slate-400">Tasks to assign:</span>
                  <span className="text-blue-300 font-mono">{pendingTasks?.length || 0}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-slate-400">Available evaluators:</span>
                  <span className="text-green-300 font-mono">{evaluators?.length || 0}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-slate-400">Devil's Advocate probability:</span>
                  <span className="text-yellow-300 font-mono">
                    {evaluators ? (calculateDevilsAdvocateProbability(evaluators.length) * 100).toFixed(1) : 0}%
                  </span>
                </div>
              </div>

              <div className="p-3 bg-yellow-950/20 border border-yellow-700 rounded-lg">
                <p className="text-yellow-300 text-sm">
                  <strong>Note:</strong> This will distribute all pending tasks to available evaluators. Evaluators will be notified immediately.
                </p>
              </div>

              <div className="flex gap-3 justify-end">
                <Button
                  variant="outline"
                  onClick={() => setShowBatchConfirmation(false)}
                  disabled={assignmentMutation.isPending}
                >
                  Cancel
                </Button>
                <Button
                  onClick={confirmBatchAssignment}
                  disabled={assignmentMutation.isPending}
                  className="bg-purple-600 hover:bg-purple-700"
                >
                  {assignmentMutation.isPending ? 'Assigning...' : 'Confirm & Assign'}
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}