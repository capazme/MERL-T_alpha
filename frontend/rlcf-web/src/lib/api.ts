import axios from 'axios';
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
} from '../types';

const axiosInstance = axios.create({
  baseURL: 'http://127.0.0.1:8000',
  timeout: 30000,
  headers: {
    'X-API-KEY': 'supersecretkey'
  }
});

// Funzione per impostare dinamicamente la chiave API
const setApiKey = (token: string | null) => {
  if (token) {
    axiosInstance.defaults.headers.common['X-API-KEY'] = token;
  } else {
    delete axiosInstance.defaults.headers.common['X-API-KEY'];
  }
};

// --- API Client ---
export const apiClient = {
  setApiKey,

  tasks: {
    list: (filters?: TaskFilters) => {
      // Convert enum values to strings for API
      const params = filters ? {
        ...filters,
        status: filters.status?.toString(),
        task_type: filters.task_type?.toString()
      } : undefined;
      return axiosInstance.get<LegalTask[]>('/tasks/all', { params }).then(res => res.data);
    },
    get: (id: number) => axiosInstance.get<LegalTask>(`/tasks/${id}`).then(res => res.data),
    create: (taskData: Partial<LegalTask>) => axiosInstance.post<LegalTask>('/tasks/', taskData).then(res => res.data),
    update: (id: number, taskData: Partial<LegalTask>) => axiosInstance.put<LegalTask>(`/tasks/${id}`, taskData).then(res => res.data),
    delete: (id: number) => axiosInstance.delete(`/tasks/${id}`).then(res => res.data),
    bulkDelete: (taskIds: number[]) => axiosInstance.post('/tasks/bulk_delete', { task_ids: taskIds }).then(res => res.data),
    bulkUpdateStatus: (taskIds: number[], status: string) => axiosInstance.post('/tasks/bulk_update_status', { task_ids: taskIds, status }).then(res => res.data),
    createBatchFromYaml: (yamlContent: string) => axiosInstance.post<LegalTask[]>('/tasks/batch_from_yaml/', { yaml_content: yamlContent }).then(res => res.data),
    updateStatus: (id: number, status: string) => axiosInstance.put<LegalTask>(`/tasks/${id}/status`, { status }).then(res => res.data),
    getAggregation: (id: number) => axiosInstance.get<AggregationResult>(`/tasks/${id}/result`).then(res => res.data),
    getResponses: (id: number) => axiosInstance.get<Response[]>(`/tasks/${id}/responses`).then(res => res.data),
    getPendingAssignments: () => axiosInstance.get<LegalTask[]>('/tasks/pending-assignments').then(res => res.data),
    getTaskTypes: () => axiosInstance.get<string[]>('/tasks/types').then(res => res.data),
    uploadCsv: (file: File, taskType?: string) => {
      const formData = new FormData();
      formData.append('file', file);
      const params = new URLSearchParams();
      if (taskType) params.append('task_type', taskType);
      return axiosInstance.post<LegalTask[]>(`/tasks/upload_csv/?${params}`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      }).then(res => res.data);
    },
    convertCsvToYaml: (file: File, taskType?: string, maxRecords?: number) => {
      const formData = new FormData();
      formData.append('file', file);
      const params = new URLSearchParams();
      if (taskType) params.append('task_type', taskType);
      if (maxRecords) params.append('max_records', maxRecords.toString());
      return axiosInstance.post(`/tasks/csv_to_yaml/?${params}`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        responseType: 'blob'
      }).then(res => res.data);
    },
  },

  users: {
    list: () => axiosInstance.get<User[]>('/users/all').then(res => res.data),
    get: (id: number) => axiosInstance.get<User>(`/users/${id}`).then(res => res.data),
    create: (username: string) => axiosInstance.post<User>('/users/', { username }).then(res => res.data),
    updateCredentials: (id: number, credentials: any) => axiosInstance.post<User>(`/users/${id}/credentials`, credentials).then(res => res.data),
    getAuthorityData: (userId: number, timeRange: string) => axiosInstance.get<any>(`/users/${userId}/authority`, { params: { timeRange } }).then(res => res.data),
    getAuthorityHistory: (userId: number, timeRange: string) => axiosInstance.get<any>(`/users/${userId}/authority/history`, { params: { timeRange } }).then(res => res.data),
    getPeerComparison: (userId: number) => axiosInstance.get<any>(`/users/${userId}/peer-comparison`).then(res => res.data),
    getAvailableEvaluators: () => axiosInstance.get<User[]>('/users/evaluators/available').then(res => res.data),
  },

  responses: {
    list: (taskId: number) => axiosInstance.get<Response[]>(`/responses/all?task_id=${taskId}`).then(res => res.data),
  },

  feedback: {
    list: (responseId?: number, userId?: number) => axiosInstance.get<Feedback[]>('/feedback/all', { params: { response_id: responseId, user_id: userId } }).then(res => res.data),
    submit: (responseId: number, feedbackData: FeedbackData) => axiosInstance.post<Feedback>(`/responses/${responseId}/feedback/`, feedbackData).then(res => res.data),
    getByTask: (taskId: number) => axiosInstance.get<Feedback[]>(`/tasks/${taskId}/feedback`).then(res => res.data),
    getByUser: (userId: number) => axiosInstance.get<Feedback[]>(`/users/${userId}/feedback`).then(res => res.data),
  },

  analytics: {
    getSystemMetrics: () => axiosInstance.get<SystemMetrics>('/analytics/system').then(res => res.data),
    getUserPerformance: (userId: number) => axiosInstance.get<PerformanceMetrics>(`/analytics/user/${userId}`).then(res => res.data),
    getLeaderboard: (limit?: number) => axiosInstance.get<User[]>('/analytics/leaderboard', { params: { limit } }).then(res => res.data),
    getTaskAnalytics: (taskId: number) => axiosInstance.get<any>(`/analytics/task/${taskId}`).then(res => res.data),
    getTaskDistribution: () => axiosInstance.get<Record<string, number>>('/analytics/task_distribution').then(res => res.data),
    getBiasAnalysis: (params: { taskId?: number; userId?: number; timeRange?: string }) => 
      axiosInstance.get<any>('/analytics/bias', { params }).then(res => res.data),
    getBiasCorrelations: (params: { taskId?: number; userId?: number; timeRange?: string }) => 
      axiosInstance.get<any>('/analytics/bias/correlations', { params }).then(res => res.data),
  },

  export: {
    dataset: (data: { task_type: TaskType, export_format: string }) => axiosInstance.post('/export/dataset', data, { responseType: 'blob' }).then(res => res.data),
    getDatasetMetrics: (options: any) => axiosInstance.post<any>('/export/metrics', options).then(res => res.data),
    generateDataset: (options: any) => axiosInstance.post<any>('/export/generate', options).then(res => res.data),
  },

  biasReports: {
    list: (userId?: number, taskId?: number) => axiosInstance.get<BiasReport[]>('/bias-reports/all', { params: { user_id: userId, task_id: taskId } }).then(res => res.data),
  },

  config: {
    getModel: () => axiosInstance.get<any>('/config/model').then(res => res.data),
    updateModel: (config: any) => axiosInstance.put<any>('/config/model', config).then(res => res.data),
    getTasks: () => axiosInstance.get<any>('/config/tasks').then(res => res.data),
    updateTasks: (config: any) => axiosInstance.put<any>('/config/tasks', config).then(res => res.data),
  },

  devilsAdvocate: {
    getAssignment: (taskId: number) => axiosInstance.get<any>(`/tasks/${taskId}/devils-advocate`).then(res => res.data),
    getCriticalPrompts: (taskType: string) => axiosInstance.get<any>(`/devils-advocate/prompts/${taskType}`).then(res => res.data),
  },

  training: {
    getCurrentCycle: () => axiosInstance.get<any>('/training/cycle').then(res => res.data),
    triggerCycle: () => axiosInstance.post<any>('/training/trigger').then(res => res.data),
  },

  ai: {
    getModels: () => axiosInstance.get<any>('/ai/models').then(res => res.data),
    generateResponse: (request: {
      task_type: string;
      input_data: any;
      model_config: {
        name: string;
        api_key: string;
        temperature?: number;
        max_tokens?: number;
      };
    }) => axiosInstance.post<any>('/ai/generate_response', request).then(res => res.data),
    getConfig: () => axiosInstance.get<any>('/ai/config').then(res => res.data),
    updateConfig: (config: any) => axiosInstance.put<any>('/ai/config', config).then(res => res.data),
    getDefaults: () => axiosInstance.get<any>('/ai/config/defaults').then(res => res.data),
  },

  admin: {
    getAssignmentStatistics: () => axiosInstance.get<any>('/admin/assignments/statistics').then(res => res.data),
    assignTasks: (assignment: { taskIds: number[], strategy: string, criteria?: any }) => 
      axiosInstance.post<any>('/admin/assignments/assign', assignment).then(res => res.data),
  },
};







export default axiosInstance;