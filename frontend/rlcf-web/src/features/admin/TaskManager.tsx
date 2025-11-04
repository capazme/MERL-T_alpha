import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Card } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { Badge } from '../../components/ui/Badge';
import { CsvUpload } from './CsvUpload';
import { apiClient } from '../../lib/api';
import type { TaskFilters, TaskStatus } from '../../types/index';

interface Task {
  id: number;
  task_type: string;
  status: string;
  created_at: string;
  input_data: any;
  ground_truth_data?: any;
}

const STATUS_COLORS = {
  OPEN: 'bg-blue-100 text-blue-800',
  BLIND_EVALUATION: 'bg-yellow-100 text-yellow-800',
  AGGREGATED: 'bg-green-100 text-green-800',
  CLOSED: 'bg-gray-100 text-gray-800',
};

const TASK_TYPE_LABELS = {
  STATUTORY_RULE_QA: 'Statutory Rule Q&A',
  QA: 'Question Answering',
  CLASSIFICATION: 'Classification',
  SUMMARIZATION: 'Summarization',
  PREDICTION: 'Prediction',
  NLI: 'Natural Language Inference',
  NER: 'Named Entity Recognition',
  DRAFTING: 'Legal Drafting',
  RISK_SPOTTING: 'Risk Spotting',
  DOCTRINE_APPLICATION: 'Doctrine Application',
};

export const TaskManager: React.FC = () => {
  const [filters, setFilters] = useState<TaskFilters>({ limit: 50 });
  const [selectedTasks, setSelectedTasks] = useState<number[]>([]);
  const [showUpload, setShowUpload] = useState(false);
  
  const queryClient = useQueryClient();

  // Fetch tasks
  const { data: tasks = [], isLoading, error } = useQuery({
    queryKey: ['tasks', filters],
    queryFn: () => apiClient.tasks.list(filters),
  });

  // Bulk delete mutation
  const deleteMutation = useMutation({
    mutationFn: (taskIds: number[]) => apiClient.tasks.bulkDelete(taskIds),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      setSelectedTasks([]);
    },
  });

  // Bulk status update mutation
  const updateStatusMutation = useMutation({
    mutationFn: ({ taskIds, status }: { taskIds: number[], status: string }) => 
      apiClient.tasks.bulkUpdateStatus(taskIds, status),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      setSelectedTasks([]);
    },
  });

  const handleSelectAll = () => {
    if (selectedTasks.length === tasks.length) {
      setSelectedTasks([]);
    } else {
      setSelectedTasks(tasks.map((task: Task) => task.id));
    }
  };

  const handleTaskSelect = (taskId: number) => {
    setSelectedTasks(prev => 
      prev.includes(taskId) 
        ? prev.filter(id => id !== taskId)
        : [...prev, taskId]
    );
  };

  const getTaskTitle = (task: Task) => {
    if (task.input_data?.question) {
      return task.input_data.question.slice(0, 100) + (task.input_data.question.length > 100 ? '...' : '');
    }
    if (task.input_data?.text) {
      return task.input_data.text.slice(0, 100) + (task.input_data.text.length > 100 ? '...' : '');
    }
    if (task.input_data?.document) {
      return task.input_data.document.slice(0, 100) + (task.input_data.document.length > 100 ? '...' : '');
    }
    return `Task #${task.id}`;
  };

  if (showUpload) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <h2 className="text-2xl font-bold text-gray-900">Upload Dataset</h2>
          <Button
            variant="outline"
            onClick={() => setShowUpload(false)}
          >
            Back to Task List
          </Button>
        </div>
        
        <CsvUpload
          onUploadComplete={(tasks) => {
            setShowUpload(false);
            queryClient.invalidateQueries({ queryKey: ['tasks'] });
          }}
        />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Task Management</h2>
          <p className="text-sm text-gray-600 mt-1">
            Manage tasks, upload datasets, and monitor progress
          </p>
        </div>
        <Button onClick={() => setShowUpload(true)}>
          Upload CSV Dataset
        </Button>
      </div>

      {/* Filters */}
      <Card className="p-4">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Status
            </label>
            <select
              value={filters.status || ''}
              onChange={(e) => setFilters(prev => ({ ...prev, status: e.target.value || undefined }))}
              className="w-full p-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
            >
              <option value="">All Statuses</option>
              <option value="OPEN">Open</option>
              <option value="BLIND_EVALUATION">Blind Evaluation</option>
              <option value="AGGREGATED">Aggregated</option>
              <option value="CLOSED">Closed</option>
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Task Type
            </label>
            <select
              value={filters.task_type || ''}
              onChange={(e) => setFilters(prev => ({ ...prev, task_type: e.target.value || undefined }))}
              className="w-full p-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
            >
              <option value="">All Types</option>
              {Object.entries(TASK_TYPE_LABELS).map(([value, label]) => (
                <option key={value} value={value}>{label}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Limit
            </label>
            <select
              value={filters.limit || ''}
              onChange={(e) => setFilters(prev => ({ ...prev, limit: e.target.value ? parseInt(e.target.value) : undefined }))}
              className="w-full p-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500"
            >
              <option value="25">25 tasks</option>
              <option value="50">50 tasks</option>
              <option value="100">100 tasks</option>
              <option value="500">500 tasks</option>
            </select>
          </div>

          <div className="flex items-end">
            <Button
              variant="outline"
              onClick={() => setFilters({ limit: 50 })}
              className="w-full"
            >
              Clear Filters
            </Button>
          </div>
        </div>
      </Card>

      {/* Bulk Actions */}
      {selectedTasks.length > 0 && (
        <Card className="p-4 bg-blue-50 border-blue-200">
          <div className="flex items-center justify-between">
            <span className="text-sm font-medium text-blue-900">
              {selectedTasks.length} task{selectedTasks.length !== 1 ? 's' : ''} selected
            </span>
            <div className="flex gap-2">
              <Button
                size="sm"
                variant="outline"
                onClick={() => updateStatusMutation.mutate({ taskIds: selectedTasks, status: 'OPEN' })}
                disabled={updateStatusMutation.isPending}
              >
                Mark Open
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={() => updateStatusMutation.mutate({ taskIds: selectedTasks, status: 'CLOSED' })}
                disabled={updateStatusMutation.isPending}
              >
                Mark Closed
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={() => deleteMutation.mutate(selectedTasks)}
                disabled={deleteMutation.isPending}
                className="text-red-600 hover:text-red-700"
              >
                Delete
              </Button>
            </div>
          </div>
        </Card>
      )}

      {/* Task List */}
      <Card>
        <div className="overflow-hidden">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left">
                  <input
                    type="checkbox"
                    checked={tasks.length > 0 && selectedTasks.length === tasks.length}
                    onChange={handleSelectAll}
                    className="rounded border-gray-300"
                  />
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Task
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Type
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Status
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Created
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {isLoading ? (
                <tr>
                  <td colSpan={6} className="px-6 py-12 text-center text-gray-500">
                    Loading tasks...
                  </td>
                </tr>
              ) : tasks.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-6 py-12 text-center text-gray-500">
                    No tasks found. Upload a CSV file to get started.
                  </td>
                </tr>
              ) : (
                tasks.map((task: Task) => (
                  <tr key={task.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4">
                      <input
                        type="checkbox"
                        checked={selectedTasks.includes(task.id)}
                        onChange={() => handleTaskSelect(task.id)}
                        className="rounded border-gray-300"
                      />
                    </td>
                    <td className="px-6 py-4">
                      <div>
                        <p className="text-sm font-medium text-gray-900">
                          {getTaskTitle(task)}
                        </p>
                        <p className="text-xs text-gray-500">ID: {task.id}</p>
                      </div>
                    </td>
                    <td className="px-6 py-4">
                      <Badge variant="outline">
                        {TASK_TYPE_LABELS[task.task_type as keyof typeof TASK_TYPE_LABELS] || task.task_type}
                      </Badge>
                    </td>
                    <td className="px-6 py-4">
                      <Badge className={STATUS_COLORS[task.status as keyof typeof STATUS_COLORS]}>
                        {task.status.replace('_', ' ')}
                      </Badge>
                    </td>
                    <td className="px-6 py-4 text-sm text-gray-500">
                      {new Date(task.created_at).toLocaleDateString()}
                    </td>
                    <td className="px-6 py-4">
                      <div className="flex gap-2">
                        <Button size="sm" variant="outline">
                          View
                        </Button>
                        <Button size="sm" variant="outline">
                          Edit
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card className="p-4">
          <div className="text-2xl font-bold text-gray-900">{tasks.length}</div>
          <div className="text-sm text-gray-600">Total Tasks</div>
        </Card>
        <Card className="p-4">
          <div className="text-2xl font-bold text-yellow-600">
            {tasks.filter((t: Task) => t.status === 'BLIND_EVALUATION').length}
          </div>
          <div className="text-sm text-gray-600">In Evaluation</div>
        </Card>
        <Card className="p-4">
          <div className="text-2xl font-bold text-green-600">
            {tasks.filter((t: Task) => t.status === 'AGGREGATED').length}
          </div>
          <div className="text-sm text-gray-600">Aggregated</div>
        </Card>
        <Card className="p-4">
          <div className="text-2xl font-bold text-gray-600">
            {tasks.filter((t: Task) => t.status === 'CLOSED').length}
          </div>
          <div className="text-sm text-gray-600">Closed</div>
        </Card>
      </div>
    </div>
  );
};