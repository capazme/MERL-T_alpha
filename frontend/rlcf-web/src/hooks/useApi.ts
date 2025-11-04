import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { apiClient } from '../lib/api';
import type {
  LegalTask,
  User,
  Feedback,
  TaskFilters,
  FeedbackData,
  SystemMetrics,
  PerformanceMetrics,
  BiasReport,
  AggregationResult,
  TaskType
} from '../types/index';
import { toast } from 'sonner';
import { useAuthStore } from '@/app/store/auth';

// Task hooks
export function useTasks(filters?: TaskFilters) {
  return useQuery({
    queryKey: ['tasks', filters],
    queryFn: () => apiClient.tasks.list(filters),
    staleTime: 2 * 60 * 1000, // 2 minutes
  });
}

export function useTask(id: number) {
  return useQuery({
    queryKey: ['task', id],
    queryFn: () => apiClient.tasks.get(id),
    enabled: !!id,
  });
}

export function useCreateTask() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: (taskData: Partial<LegalTask>) => apiClient.tasks.create(taskData),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      toast.success('Task created successfully!');
    },
    onError: (error: any) => {
      toast.error(error?.response?.data?.message || 'Failed to create task');
    },
  });
}

export function useBatchCreateTasksFromYaml() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (yamlContent: string) => apiClient.tasks.createBatchFromYaml(yamlContent),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      toast.success('Batch tasks created successfully!');
    },
    onError: (error: any) => {
      let errorMessage = 'Failed to create tasks from YAML.';
      if (error?.response?.data?.detail) {
        if (Array.isArray(error.response.data.detail)) {
          errorMessage = error.response.data.detail.map((e: any) => `Field: '${e.loc.join('.')}', Error: ${e.msg}`).join('; ');
        } else {
          errorMessage = JSON.stringify(error.response.data.detail);
        }
      } else if (error?.response?.data?.message) {
        errorMessage = error.response.data.message;
      }
      toast.error(`Batch creation failed: ${errorMessage}`, { duration: 10000 });
    },
  });
}

export function useUpdateTaskStatus() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({ id, status }: { id: number; status: string }) => {
      // Assicurati che il token sia caricato prima di fare la chiamata
      const token = useAuthStore.getState().token;
      if (!token) {
        throw new Error("API token not available");
      }
      apiClient.setApiKey(token);
      return apiClient.tasks.updateStatus(id, status);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      toast.success('Task status updated!');
    },
    onError: (error: any) => {
      toast.error(error?.response?.data?.detail || 'Failed to update task status');
    }
  });
}

export function useTaskAggregation(taskId: number) {
  return useQuery({
    queryKey: ['task-aggregation', taskId],
    queryFn: () => apiClient.tasks.getAggregation(taskId),
    enabled: !!taskId,
    refetchInterval: 5000, // Refetch every 5 seconds for live updates
  });
}

// User hooks
export function useUsers() {
  return useQuery({
    queryKey: ['users'],
    queryFn: () => apiClient.users.list(),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

export function useUser(id: number) {
  return useQuery({
    queryKey: ['user', id],
    queryFn: () => apiClient.users.get(id),
    enabled: !!id,
  });
}

export function useUserAuthority(id: number) {
  // Backend non espone /users/{id}/authority; deriviamo dal dettaglio utente
  return useQuery({
    queryKey: ['user-authority', id],
    queryFn: async () => {
      const user = await apiClient.users.get(id);
      return { authority_score: user.authority_score } as { authority_score: number };
    },
    enabled: !!id,
    staleTime: 60 * 1000,
  });
}

export function useUpdateUserCredentials() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: ({ id, credentials }: { id: number; credentials: Record<string, any> }) =>
      apiClient.users.updateCredentials(id, credentials),
    onSuccess: (data, variables) => {
      queryClient.invalidateQueries({ queryKey: ['user', variables.id] });
      queryClient.invalidateQueries({ queryKey: ['user-authority', variables.id] });
      toast.success('Credentials updated successfully!');
    },
  });
}

export function useCreateUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (username: string) => apiClient.users.create(username),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users'] });
      toast.success('User created successfully!');
    },
    onError: (error: any) => {
      toast.error(error?.response?.data?.message || 'Failed to create user');
    },
  });
}

export function useAddCredential() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, credential }: { id: number; credential: Record<string, any> }) =>
      apiClient.users.updateCredentials(id, credential),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ['user', variables.id] });
      toast.success('Credential added successfully!');
    },
  });
}

export function useSetApiKey() {
  return useMutation({
    mutationFn: (token: string | null) => {
      apiClient.setApiKey(token);
      return Promise.resolve();
    },
  });
}

// Feedback hooks
export function useFeedback(responseId?: number, userId?: number) {
  return useQuery({
    queryKey: ['feedback', { responseId, userId }],
    queryFn: () => apiClient.feedback.list(responseId, userId),
    enabled: !!(responseId || userId),
  });
}

export function useSubmitFeedback() {
  const queryClient = useQueryClient();
  const { token } = useAuthStore.getState(); // Get token for API key

  return useMutation({
    mutationKey: ['submit-feedback'],
    mutationFn: ({ responseId, feedbackData }: { responseId: number; feedbackData: FeedbackData }) => {
      apiClient.setApiKey(token);
      return apiClient.feedback.submit(responseId, feedbackData);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      queryClient.invalidateQueries({ queryKey: ['feedback'] });
      queryClient.invalidateQueries({ queryKey: ['user-performance'] });
      queryClient.invalidateQueries({ queryKey: ['analytics'] });
    },
  });
}

// Analytics hooks
export function useSystemMetrics() {
  return useQuery({
    queryKey: ['system-metrics'],
    queryFn: () => apiClient.analytics.getSystemMetrics(),
    staleTime: 30 * 1000, // 30 seconds
    refetchInterval: 60 * 1000, // Refetch every minute
  });
}

export function useUserPerformance(userId: number) {
  return useQuery({
    queryKey: ['user-performance', userId],
    queryFn: () => apiClient.analytics.getUserPerformance(userId),
    enabled: !!userId,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

export function useLeaderboard(limit?: number) {
  return useQuery({
    queryKey: ['leaderboard', limit],
    queryFn: () => apiClient.analytics.getLeaderboard(limit),
    staleTime: 2 * 60 * 1000, // 2 minutes
  });
}

export function useTaskAnalytics(taskId: number) {
  return useQuery({
    queryKey: ['task-analytics', taskId],
    queryFn: () => apiClient.analytics.getTaskAnalytics(taskId),
    enabled: !!taskId,
    staleTime: 1 * 60 * 1000, // 1 minute
  });
}

export function useExportDataset() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (data: { task_type: TaskType, export_format: string }) => {
      const token = useAuthStore.getState().token;
      if (!token) {
        throw new Error("API token not available");
      }
      apiClient.setApiKey(token);
      return apiClient.export.dataset(data);
    },
    onSuccess: (blob, variables) => {
      const url = window.URL.createObjectURL(new Blob([blob]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `${variables.task_type}_${variables.export_format}.jsonl`);
      document.body.appendChild(link);
      link.click();
      link.parentNode?.removeChild(link);
      toast.success('Dataset exported successfully!');
    },
    onError: (error: any) => {
      toast.error(error?.response?.data?.detail || 'Failed to export dataset');
    }
  });
}

export function useTaskDistribution() {
  return useQuery({
    queryKey: ['task-distribution'],
    queryFn: () => apiClient.analytics.getTaskDistribution(),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

// Bias reports
export function useBiasReports(userId?: number, taskId?: number) {
  return useQuery({
    queryKey: ['bias-reports', { userId, taskId }],
    queryFn: () => apiClient.biasReports.list(userId, taskId),
    enabled: !!(userId || taskId),
  });
}

// Configuration hooks
export function useModelConfig() {
  return useQuery({
    queryKey: ['config', 'model'],
    queryFn: () => apiClient.config.getModel(),
    staleTime: 10 * 60 * 1000, // 10 minutes
  });
}

export function useTaskConfig() {
  return useQuery({
    queryKey: ['config', 'tasks'],
    queryFn: () => apiClient.config.getTasks(),
    staleTime: 10 * 60 * 1000, // 10 minutes
  });
}

export function useUpdateModelConfig() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationKey: ['update-config'],
    mutationFn: (config: any) => apiClient.config.updateModel(config),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['config', 'model'] });
    },
  });
}

export function useUpdateTaskConfig() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationKey: ['update-config'],
    mutationFn: (config: any) => apiClient.config.updateTasks(config),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['config', 'tasks'] });
    },
  });
}

// Devil's advocate hooks
export function useDevilsAdvocateAssignment(taskId: number) {
  return useQuery({
    queryKey: ['devils-advocate', taskId],
    queryFn: () => apiClient.devilsAdvocate.getAssignment(taskId),
    enabled: !!taskId,
  });
}

export function useDevilsAdvocatePrompts(taskType: string) {
  return useQuery({
    queryKey: ['devils-advocate-prompts', taskType],
    queryFn: () => apiClient.devilsAdvocate.getCriticalPrompts(taskType),
    enabled: !!taskType,
    staleTime: 30 * 60 * 1000, // 30 minutes
  });
}

// Training hooks
export function useCurrentTrainingCycle() {
  return useQuery({
    queryKey: ['training', 'current-cycle'],
    queryFn: () => apiClient.training.getCurrentCycle(),
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

export function useTriggerTrainingCycle() {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: () => apiClient.training.triggerCycle(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['training'] });
      toast.success('Training cycle triggered!');
    },
  });
}
