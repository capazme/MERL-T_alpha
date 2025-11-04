// Core RLCF Types
export interface User {
  id: number;
  username: string;
  email?: string;
  authority_score: number;
  track_record_score: number;
  baseline_credential_score: number;
  credentials?: any[];
  created_at?: string;
  updated_at?: string;
  tasks_completed?: number;
  recent_performance?: number;
}

export interface LegalTask {
  id: number;
  task_type: string;
  input_data: Record<string, any>;
  ground_truth_data: Record<string, any> | null;
  status: string;
  created_at: string;
  evaluator_count?: number;
  deadline?: string;
  description?: string;
}

export interface Response {
  id: number;
  task_id: number;
  model_version: string;
  output_data: Record<string, any>;
  generated_at: string;
}

export interface Feedback {
  id: number;
  user_id: number;
  response_id: number;
  feedback_data: Record<string, any>;
  is_devils_advocate: boolean;
  created_at: string;
  user?: User;
  accuracy_score?: number;
  utility_score?: number;
  transparency_score?: number;
  metadata?: Record<string, any>;
}

export interface BiasReport {
  id: number;
  user_id: number;
  task_id: number;
  bias_scores: Record<string, number>;
  recommendations: string[];
  created_at: string;
}

export interface AggregationResult {
  task_id: number;
  primary_answer: string;
  confidence: number;
  positions: AlternativePosition[];
  disagreement_score: number;
  consensus_level: number;
  uncertainty_metrics: UncertaintyMetrics;
}

export interface AlternativePosition {
  position: string;
  support: number;
  supporters: User[];
  reasoning: string[];
  confidence: number;
}

export interface UncertaintyMetrics {
  shannon_entropy: number;
  position_diversity: number;
  reasoning_complexity: number;
}

// Const objects (instead of enums for erasableSyntaxOnly compatibility)
export const TaskStatus = {
  OPEN: 'OPEN',
  BLIND_EVALUATION: 'BLIND_EVALUATION',
  AGGREGATED: 'AGGREGATED',
  CLOSED: 'CLOSED'
} as const;

export type TaskStatus = typeof TaskStatus[keyof typeof TaskStatus];

export const TaskType = {
  SUMMARIZATION: 'SUMMARIZATION',
  CLASSIFICATION: 'CLASSIFICATION',
  QA: 'QA',
  STATUTORY_RULE_QA: 'STATUTORY_RULE_QA',
  PREDICTION: 'PREDICTION',
  NLI: 'NLI',
  NER: 'NER',
  DRAFTING: 'DRAFTING',
  RISK_SPOTTING: 'RISK_SPOTTING',
  DOCTRINE_APPLICATION: 'DOCTRINE_APPLICATION'
} as const;

export type TaskType = typeof TaskType[keyof typeof TaskType];

export const UserRole = {
  ADMIN: 'admin',
  EVALUATOR: 'evaluator',
  VIEWER: 'viewer'
} as const;

export type UserRole = typeof UserRole[keyof typeof UserRole];

// UI Component Types
export interface DashboardMode {
  admin: {
    configManagement: boolean;
    taskCreation: boolean;
    systemAnalytics: boolean;
    userManagement: boolean;
  };
  evaluator: {
    taskEvaluation: boolean;
    profileView: boolean;
    performanceTracking: boolean;
  };
  viewer: {
    publicStats: boolean;
    leaderboard: boolean;
  };
}

export interface AuthorityScoreBreakdown {
  baseline: number;
  trackRecord: number;
  recentPerformance: number;
}

export interface TaskCardProps {
  task: LegalTask;
  onSelect?: (task: LegalTask) => void;
  showDetails?: boolean;
}

export interface AuthorityScoreCardProps {
  userId: number;
  score: number;
  trend: 'up' | 'down' | 'stable';
  percentile: number;
  breakdown: AuthorityScoreBreakdown;
  animated?: boolean;
}

export interface BiasMetrics {
  demographic: number;
  professional: number;
  temporal: number;
  geographic: number;
  confirmation: number;
  anchoring: number;
}

export interface BiasRecommendation {
  type: string;
  severity: 'low' | 'medium' | 'high';
  description: string;
  action: string;
}

// New Types for Frontend Components
export type ExportFormat = 'sft' | 'preference' | 'research' | 'csv';

export interface DatasetMetrics {
  totalTasks: number;
  totalFeedback: number;
  avgAuthorityScore: number;
  taskTypeDistribution: { type: string; count: number }[];
  qualityMetrics: {
    avgAccuracy: number;
    avgUtility: number;
    avgTransparency: number;
  };
  uncertaintyDistribution: { level: string; count: number }[];
}

export interface AuthorityHistory {
  timestamp: string;
  authority_score: number;
  baseline_credentials: number;
  track_record: number;
  recent_performance: number;
}

export interface AuthorityBreakdown {
  baseline_credentials: number;
  track_record: number;
  recent_performance: number;
  peer_validation_rate?: number;
  consistency_score?: number;
  domain_expertise?: number;
}

export interface BiasMetrics {
  [key: string]: number;
}

export interface BiasAnalysis {
  dimensions: BiasMetrics;
  detections?: any[];
  timeline?: any[];
}

export interface TaskAssignment {
  id: number;
  task_id: number;
  user_id: number;
  assigned_at: string;
  completed_at?: string;
  status: 'pending' | 'in_progress' | 'completed';
  is_devils_advocate: boolean;
}

export interface AssignmentCriteria {
  min_authority?: number;
  max_concurrent?: number;
  require_expertise?: boolean;
  enable_devils_advocate?: boolean;
}

// API Types
export interface TaskFilters {
  status?: TaskStatus;
  task_type?: TaskType;
  limit?: number;
  offset?: number;
  user_id?: number;
}

export interface FeedbackData {
  [key: string]: any;
}

export interface ConfigUpdate {
  authority_weights?: Record<string, number>;
  thresholds?: Record<string, number>;
  task_schemas?: Record<string, any>;
}

// Evaluation Flow Types
export interface EvaluationStep {
  id: number;
  title: string;
  description: string;
  component: string;
  required: boolean;
}

export interface EvaluationWizardState {
  currentStep: number;
  taskId: number;
  responseId: number;
  isDevilsAdvocate: boolean;
  formData: Record<string, any>;
  completed: boolean;
  startTime: number;
}

// Analytics Types
export interface SystemMetrics {
  totalTasks: number;
  totalUsers: number;
  totalFeedback: number;
  averageConsensus: number;
  activeEvaluations: number;
  completionRate: number;
}

export interface PerformanceMetrics {
  accuracy: number;
  consistency: number;
  throughput: number;
  qualityScore: number;
  biasScore: number;
  percentile_rank?: number;
}

// WebSocket Types
export interface WebSocketMessage {
  type: 'NEW_FEEDBACK' | 'AGGREGATION_COMPLETE' | 'TASK_UPDATE' | 'AUTHORITY_UPDATE';
  data: any;
  timestamp: string;
}

export interface RealtimeUpdate {
  taskId?: number;
  userId?: number;
  message: string;
  type: 'info' | 'success' | 'warning' | 'error';
}