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

// Orchestration API (porta 8000) - per query e orchestrazione
const axiosInstance = axios.create({
  baseURL: 'http://127.0.0.1:8000',
  timeout: 70000, // 70s to allow for 60s backend timeout + margin
  headers: {
    'X-API-KEY': 'merl-t-admin-key-dev-only-change-in-production'  // Development admin key from migration
  }
});

// RLCF API (porta 8001) - per utenti, tasks, feedback
const rlcfAxios = axios.create({
  baseURL: 'http://127.0.0.1:8001',
  timeout: 70000, // 70s to allow for 60s backend timeout + margin
  headers: {
    'X-API-KEY': 'merl-t-admin-key-dev-only-change-in-production'  // Development admin key from migration
  }
});

// Ingestion API (porta 8002) - per KG ingestion e batch processing
const ingestionAxios = axios.create({
  baseURL: 'http://127.0.0.1:8002',
  timeout: 60000, // Timeout più lungo per batch processing
  headers: {
    'X-API-KEY': 'merl-t-admin-key-dev-only-change-in-production'  // Development admin key from migration
  }
});

// Funzione per impostare dinamicamente la chiave API
const setApiKey = (token: string | null) => {
  if (token) {
    axiosInstance.defaults.headers.common['X-API-KEY'] = token;
    rlcfAxios.defaults.headers.common['X-API-KEY'] = token;
    ingestionAxios.defaults.headers.common['X-API-KEY'] = token;
  } else {
    delete axiosInstance.defaults.headers.common['X-API-KEY'];
    delete rlcfAxios.defaults.headers.common['X-API-KEY'];
    delete ingestionAxios.defaults.headers.common['X-API-KEY'];
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
      return rlcfAxios.get<LegalTask[]>('/tasks/all', { params }).then(res => res.data);
    },
    get: (id: number) => rlcfAxios.get<LegalTask>(`/tasks/${id}`).then(res => res.data),
    create: (taskData: Partial<LegalTask>) => rlcfAxios.post<LegalTask>('/tasks/', taskData).then(res => res.data),
    update: (id: number, taskData: Partial<LegalTask>) => rlcfAxios.put<LegalTask>(`/tasks/${id}`, taskData).then(res => res.data),
    delete: (id: number) => rlcfAxios.delete(`/tasks/${id}`).then(res => res.data),
    bulkDelete: (taskIds: number[]) => rlcfAxios.post('/tasks/bulk_delete', { task_ids: taskIds }).then(res => res.data),
    bulkUpdateStatus: (taskIds: number[], status: string) => rlcfAxios.post('/tasks/bulk_update_status', { task_ids: taskIds, status }).then(res => res.data),
    createBatchFromYaml: (yamlContent: string) => rlcfAxios.post<LegalTask[]>('/tasks/batch_from_yaml/', { yaml_content: yamlContent }).then(res => res.data),
    updateStatus: (id: number, status: string) => rlcfAxios.put<LegalTask>(`/tasks/${id}/status`, { status }).then(res => res.data),
    getAggregation: (id: number) => rlcfAxios.get<AggregationResult>(`/tasks/${id}/result`).then(res => res.data),
    getResponses: (id: number) => rlcfAxios.get<Response[]>(`/tasks/${id}/responses`).then(res => res.data),
    getPendingAssignments: () => rlcfAxios.get<LegalTask[]>('/tasks/pending-assignments').then(res => res.data),
    getTaskTypes: () => rlcfAxios.get<string[]>('/tasks/types').then(res => res.data),
    uploadCsv: (file: File, taskType?: string) => {
      const formData = new FormData();
      formData.append('file', file);
      const params = new URLSearchParams();
      if (taskType) params.append('task_type', taskType);
      return rlcfAxios.post<LegalTask[]>(`/tasks/upload_csv/?${params}`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      }).then(res => res.data);
    },
    convertCsvToYaml: (file: File, taskType?: string, maxRecords?: number) => {
      const formData = new FormData();
      formData.append('file', file);
      const params = new URLSearchParams();
      if (taskType) params.append('task_type', taskType);
      if (maxRecords) params.append('max_records', maxRecords.toString());
      return rlcfAxios.post(`/tasks/csv_to_yaml/?${params}`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        responseType: 'blob'
      }).then(res => res.data);
    },
  },

  users: {
    list: () => rlcfAxios.get<User[]>('/users/all').then(res => res.data),
    get: (id: number) => rlcfAxios.get<User>(`/users/${id}`).then(res => res.data),
    create: (username: string) => rlcfAxios.post<User>('/users/', { username }).then(res => res.data),
    updateCredentials: (id: number, credentials: any) => rlcfAxios.post<User>(`/users/${id}/credentials`, credentials).then(res => res.data),
    getAuthorityData: (userId: number, timeRange: string) => rlcfAxios.get<any>(`/users/${userId}/authority`, { params: { timeRange } }).then(res => res.data),
    getAuthorityHistory: (userId: number, timeRange: string) => rlcfAxios.get<any>(`/users/${userId}/authority/history`, { params: { timeRange } }).then(res => res.data),
    getPeerComparison: (userId: number) => rlcfAxios.get<any>(`/users/${userId}/peer-comparison`).then(res => res.data),
    getAvailableEvaluators: () => rlcfAxios.get<User[]>('/users/evaluators/available').then(res => res.data),
  },

  responses: {
    list: (taskId: number) => rlcfAxios.get<Response[]>(`/responses/all?task_id=${taskId}`).then(res => res.data),
  },

  feedback: {
    list: (responseId?: number, userId?: number) => rlcfAxios.get<Feedback[]>('/feedback/all', { params: { response_id: responseId, user_id: userId } }).then(res => res.data),
    submit: (responseId: number, feedbackData: FeedbackData) => rlcfAxios.post<Feedback>(`/responses/${responseId}/feedback/`, feedbackData).then(res => res.data),
    getByTask: (taskId: number) => rlcfAxios.get<Feedback[]>(`/tasks/${taskId}/feedback`).then(res => res.data),
    getByUser: (userId: number) => rlcfAxios.get<Feedback[]>(`/users/${userId}/feedback`).then(res => res.data),
  },

  analytics: {
    getSystemMetrics: () => rlcfAxios.get<SystemMetrics>('/analytics/system').then(res => res.data),
    getUserPerformance: (userId: number) => rlcfAxios.get<PerformanceMetrics>(`/analytics/user/${userId}`).then(res => res.data),
    getLeaderboard: (limit?: number) => rlcfAxios.get<User[]>('/analytics/leaderboard', { params: { limit } }).then(res => res.data),
    getTaskAnalytics: (taskId: number) => rlcfAxios.get<any>(`/analytics/task/${taskId}`).then(res => res.data),
    getTaskDistribution: () => rlcfAxios.get<Record<string, number>>('/analytics/task_distribution').then(res => res.data),
    getBiasAnalysis: (params: { taskId?: number; userId?: number; timeRange?: string }) =>
      rlcfAxios.get<any>('/analytics/bias', { params }).then(res => res.data),
    getBiasCorrelations: (params: { taskId?: number; userId?: number; timeRange?: string }) =>
      rlcfAxios.get<any>('/analytics/bias/correlations', { params }).then(res => res.data),
  },

  export: {
    dataset: (data: { task_type: TaskType, export_format: string }) => rlcfAxios.post('/export/dataset', data, { responseType: 'blob' }).then(res => res.data),
    getDatasetMetrics: (options: any) => rlcfAxios.post<any>('/export/metrics', options).then(res => res.data),
    generateDataset: (options: any) => rlcfAxios.post<any>('/export/generate', options).then(res => res.data),
  },

  biasReports: {
    list: (userId?: number, taskId?: number) => rlcfAxios.get<BiasReport[]>('/bias-reports/all', { params: { user_id: userId, task_id: taskId } }).then(res => res.data),
  },

  config: {
    getModel: () => rlcfAxios.get<any>('/config/model').then(res => res.data),
    updateModel: (config: any) => rlcfAxios.put<any>('/config/model', config).then(res => res.data),
    getTasks: () => rlcfAxios.get<any>('/config/tasks').then(res => res.data),
    updateTasks: (config: any) => rlcfAxios.put<any>('/config/tasks', config).then(res => res.data),
  },

  devilsAdvocate: {
    getAssignment: (taskId: number) => rlcfAxios.get<any>(`/tasks/${taskId}/devils-advocate`).then(res => res.data),
    getCriticalPrompts: (taskType: string) => rlcfAxios.get<any>(`/devils-advocate/prompts/${taskType}`).then(res => res.data),
  },

  training: {
    getCurrentCycle: () => rlcfAxios.get<any>('/training/cycle').then(res => res.data),
    triggerCycle: () => rlcfAxios.post<any>('/training/trigger').then(res => res.data),
  },

  ai: {
    getModels: () => rlcfAxios.get<any>('/ai/models').then(res => res.data),
    generateResponse: (request: {
      task_type: string;
      input_data: any;
      model_config: {
        name: string;
        api_key: string;
        temperature?: number;
        max_tokens?: number;
      };
    }) => rlcfAxios.post<any>('/ai/generate_response', request).then(res => res.data),
    getConfig: () => rlcfAxios.get<any>('/ai/config').then(res => res.data),
    updateConfig: (config: any) => rlcfAxios.put<any>('/ai/config', config).then(res => res.data),
    getDefaults: () => rlcfAxios.get<any>('/ai/config/defaults').then(res => res.data),
  },

  admin: {
    getAssignmentStatistics: () => rlcfAxios.get<any>('/admin/assignments/statistics').then(res => res.data),
    assignTasks: (assignment: { taskIds: number[], strategy: string, criteria?: any }) =>
      rlcfAxios.post<any>('/admin/assignments/assign', assignment).then(res => res.data),
  },

  orchestration: {
    // Query execution and monitoring
    executeQuery: (request: { query: string; context?: any; options?: any }) =>
      axiosInstance.post<any>('/query/execute', request).then(res => res.data),

    getQueryStatus: (traceId: string) =>
      axiosInstance.get<any>(`/query/status/${traceId}`).then(res => res.data),

    getQueryHistory: (userId: string, params?: { limit?: number; offset?: number; since?: string }) =>
      axiosInstance.get<any>(`/query/history/${userId}`, { params }).then(res => res.data),

    retrieveQuery: (traceId: string) =>
      axiosInstance.get<any>(`/query/retrieve/${traceId}`).then(res => res.data),

    // Feedback submission
    submitUserFeedback: (feedback: { trace_id: string; rating: number; feedback_text?: string; categories?: any }) =>
      axiosInstance.post<any>('/feedback/user', feedback).then(res => res.data),

    submitRlcfFeedback: (feedback: { trace_id: string; expert_id: number; authority_score: number; corrections: any }) =>
      axiosInstance.post<any>('/feedback/rlcf', feedback).then(res => res.data),

    submitNerCorrection: (correction: { trace_id: string; expert_id: number; correction_type: string; original_entity: any; corrected_entity: any }) =>
      axiosInstance.post<any>('/feedback/ner', correction).then(res => res.data),

    // Statistics
    getFeedbackStats: () =>
      axiosInstance.get<any>('/feedback/stats').then(res => res.data),
  },

  ingestion: {
    // Batch management
    createBatch: (config: any) =>
      ingestionAxios.post<any>('/batch/create', config).then(res => res.data),

    getBatch: (batchId: string) =>
      ingestionAxios.get<any>(`/batch/${batchId}`).then(res => res.data),

    listBatches: (params?: { status?: string; limit?: number; offset?: number }) =>
      ingestionAxios.get<any>('/batch/list', { params }).then(res => res.data),

    startBatch: (batchId: string) =>
      ingestionAxios.post<any>(`/batch/${batchId}/start`).then(res => res.data),

    pauseBatch: (batchId: string) =>
      ingestionAxios.post<any>(`/batch/${batchId}/pause`).then(res => res.data),

    cancelBatch: (batchId: string) =>
      ingestionAxios.post<any>(`/batch/${batchId}/cancel`).then(res => res.data),

    getBatchProgress: (batchId: string) =>
      ingestionAxios.get<any>(`/batch/${batchId}/progress`).then(res => res.data),

    // Entity validation
    validateEntity: (entity: any) =>
      ingestionAxios.post<any>('/validate/entity', entity).then(res => res.data),

    // Health check
    getHealth: () =>
      ingestionAxios.get<any>('/health').then(res => res.data),
  },
};







export default axiosInstance;