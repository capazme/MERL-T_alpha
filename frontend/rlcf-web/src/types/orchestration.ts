/**
 * Orchestration API Types
 *
 * TypeScript types for orchestration API requests and responses.
 * Aligned with backend Pydantic schemas in backend/orchestration/api/schemas/
 */

// ============================================================================
// REQUEST TYPES
// ============================================================================

/**
 * Optional execution parameters for query
 */
export interface QueryOptions {
  /** Maximum refinement iterations (1-10) */
  max_iterations?: number;
  /** Include full execution trace in response */
  return_trace?: boolean;
  /** Enable SSE streaming (future feature) */
  stream_response?: boolean;
  /** Query timeout in milliseconds (1000-120000) */
  timeout_ms?: number;
}

/**
 * Additional context for query understanding
 */
export interface QueryContext {
  /** Temporal reference for legal interpretation (ISO date or 'latest') */
  temporal_reference?: string | null;
  /** Legal jurisdiction scope */
  jurisdiction?: 'nazionale' | 'regionale' | 'comunitario' | string;
  /** User role for context-aware responses */
  user_role?: 'cittadino' | 'avvocato' | 'giudice' | 'studente' | string;
  /** Previous queries in conversation (multi-turn context) */
  previous_queries?: string[] | null;
}

/**
 * Main request schema for POST /query/execute endpoint
 */
export interface QueryRequest {
  /** Legal query text (10-2000 chars) */
  query: string;
  /** Session ID for multi-turn conversations */
  session_id?: string | null;
  /** Additional query context */
  context?: QueryContext | null;
  /** Execution options */
  options?: QueryOptions | null;
}

// ============================================================================
// RESPONSE TYPES
// ============================================================================

/**
 * Reference to a legal norm supporting the answer
 */
export interface LegalBasis {
  /** Unique norm identifier */
  norm_id: string;
  /** Norm title or description */
  norm_title: string;
  /** Specific article/section */
  article?: string | null;
  /** Relevance score (0-1) */
  relevance: number;
  /** Relevant text excerpt */
  excerpt?: string | null;
}

/**
 * Jurisprudence (case law) reference
 */
export interface Jurisprudence {
  /** Case identifier (e.g., "Cass. n. 12345/2024") */
  case_id: string;
  /** Court name */
  court: string;
  /** Decision date */
  date?: string | null;
  /** Brief summary or massima */
  summary?: string | null;
  /** Relevance score (0-1) */
  relevance: number;
  /** Link to full text (if available) */
  link?: string | null;
}

/**
 * Alternative legal interpretation with minority support
 */
export interface AlternativeInterpretation {
  /** Alternative interpretation text */
  position: string;
  /** Level of legal support for this interpretation */
  support_level: 'minority' | 'contested' | 'emerging';
  /** Norm IDs supporting this interpretation */
  supporting_norms: string[];
  /** Case law supporting this interpretation */
  supporting_jurisprudence?: string[] | null;
  /** Explanation of this alternative view */
  reasoning?: string | null;
  /** Experts supporting this interpretation */
  supporting_experts?: string[];
}

/**
 * Complete legal answer with supporting evidence
 */
export interface Answer {
  /** Main legal answer synthesized from expert opinions */
  primary_answer: string;
  /** Overall confidence score (0-1) */
  confidence: number;
  /** Norms and legal sources supporting the answer */
  legal_basis: LegalBasis[];
  /** Relevant case law (sentenze) */
  jurisprudence?: Jurisprudence[] | null;
  /** Alternative legal interpretations (if any) */
  alternative_interpretations?: AlternativeInterpretation[] | null;
  /** Whether expert disagreement was preserved (RLCF principle) */
  uncertainty_preserved: boolean;
  /** Expert consensus level (0-1, if multiple experts consulted) */
  consensus_level?: number | null;
}

/**
 * Expert opinion details
 */
export interface ExpertOpinion {
  /** Expert type (literal_interpreter, systemic_teleological, etc.) */
  expert_type: string;
  /** Expert's answer */
  opinion: string;
  /** Confidence score (0-1) */
  confidence: number;
  /** Reasoning behind the opinion */
  reasoning?: string | null;
  /** Supporting evidence */
  supporting_evidence?: string[] | null;
}

/**
 * Complete execution trace for observability
 */
export interface ExecutionTrace {
  /** Unique trace identifier */
  trace_id: string;
  /** Pipeline stages executed in order */
  stages_executed: string[];
  /** Number of refinement iterations */
  iterations: number;
  /** Reason for stopping iteration (if applicable) */
  stop_reason?: string | null;
  /** Expert types activated for this query */
  experts_consulted: string[];
  /** Retrieval agents used (kg_agent, api_agent, vectordb_agent) */
  agents_used: string[];
  /** Total execution time (ms) */
  total_time_ms: number;
  /** Per-stage execution times (ms) */
  stage_timings?: Record<string, number> | null;
  /** Total LLM tokens consumed */
  tokens_used?: number | null;
  /** Non-fatal errors encountered during execution */
  errors: string[];
  /** Detailed expert opinions (if available) */
  expert_opinions?: ExpertOpinion[] | null;
}

/**
 * Metadata about query processing
 */
export interface AnswerMetadata {
  /** Query complexity score (0-1) */
  complexity_score: number;
  /** Detected query intent category */
  intent_detected: string;
  /** Legal concepts extracted from query */
  concepts_identified: string[];
  /** Named entities extracted (NER) */
  entities_identified?: Array<{ text: string; type: string; span: [number, number] }> | null;
  /** Number of norms consulted */
  norms_consulted: number;
  /** Number of cases consulted */
  jurisprudence_consulted: number;
  /** Synthesis mode used */
  synthesis_mode?: 'convergent' | 'divergent' | null;
}

/**
 * Complete response for POST /query/execute endpoint
 */
export interface QueryResponse {
  /** Unique trace identifier for this query */
  trace_id: string;
  /** Session ID (if provided) */
  session_id?: string | null;
  /** Complete legal answer */
  answer: Answer;
  /** Full execution trace (if return_trace=True) */
  execution_trace?: ExecutionTrace | null;
  /** Query processing metadata */
  metadata: AnswerMetadata;
  /** Response timestamp (UTC) */
  timestamp: string;
  /** Original query text */
  query?: string;
}

// ============================================================================
// QUERY STATUS TYPES
// ============================================================================

/**
 * Query execution status
 */
export type QueryStatus = 'pending' | 'processing' | 'completed' | 'failed';

/**
 * Query status response for GET /query/status/{trace_id}
 */
export interface QueryStatusResponse {
  /** Trace ID */
  trace_id: string;
  /** Current status */
  status: QueryStatus;
  /** Progress percentage (0-100) */
  progress_percent: number;
  /** Current stage being executed */
  current_stage?: string | null;
  /** Estimated time remaining (seconds) */
  eta_seconds?: number | null;
  /** Error message (if status=failed) */
  error?: string | null;
}

// ============================================================================
// QUERY HISTORY TYPES
// ============================================================================

/**
 * Query history item
 */
export interface QueryHistoryItem {
  /** Trace ID */
  trace_id: string;
  /** Original query text */
  query: string;
  /** Query status */
  status: QueryStatus;
  /** Submission timestamp */
  timestamp: string;
  /** Confidence score (if completed) */
  confidence?: number | null;
  /** Preview of answer (first 100 chars) */
  answer_preview?: string | null;
}

/**
 * Query history response for GET /query/history/{user_id}
 */
export interface QueryHistoryResponse {
  /** User ID */
  user_id: string;
  /** Query history items */
  queries: QueryHistoryItem[];
  /** Total count of queries */
  total_count: number;
  /** Number of items returned */
  limit: number;
  /** Offset for pagination */
  offset: number;
}

// ============================================================================
// FEEDBACK TYPES
// ============================================================================

/**
 * User feedback request for POST /feedback/user
 */
export interface UserFeedbackRequest {
  /** Trace ID of the query being reviewed */
  trace_id: string;
  /** Star rating (1-5) */
  rating: number;
  /** Optional feedback text */
  feedback_text?: string | null;
  /** Feedback categories */
  categories?: {
    accuracy?: boolean;
    completeness?: boolean;
    clarity?: boolean;
    usefulness?: boolean;
  } | null;
}

/**
 * RLCF expert feedback corrections
 */
export interface RLCFFeedbackCorrections {
  /** Concept mapping corrections */
  concept_mapping?: {
    incorrect_entities?: string[];
    missing_entities?: string[];
    incorrect_intent?: string | null;
    correct_intent?: string | null;
  } | null;
  /** Routing corrections */
  routing?: {
    unnecessary_experts?: string[];
    missing_experts?: string[];
    inappropriate_agents?: string[];
  } | null;
  /** Answer quality vote */
  answer_quality?: {
    vote: 'approve' | 'reject' | 'uncertain';
    reasoning: string;
    suggested_improvements?: string | null;
  } | null;
}

/**
 * RLCF expert feedback request for POST /feedback/rlcf
 */
export interface RLCFFeedbackRequest {
  /** Trace ID */
  trace_id: string;
  /** Expert ID (user ID of the expert) */
  expert_id: string;
  /** Expert's authority score (read-only, for display) */
  authority_score?: number;
  /** Detailed corrections */
  corrections: RLCFFeedbackCorrections;
}

/**
 * NER correction types
 */
export type NERCorrectionType = 'ADD_ENTITY' | 'REMOVE_ENTITY' | 'CORRECT_TYPE' | 'CORRECT_SPAN';

/**
 * NER correction request for POST /feedback/ner
 */
export interface NERCorrectionRequest {
  /** Trace ID */
  trace_id: string;
  /** Type of correction */
  correction_type: NERCorrectionType;
  /** Correction data */
  correction_data: {
    /** Entity text */
    entity_text: string;
    /** Entity type (e.g., "NORMA", "SENTENZA", "ISTITUZIONE") */
    entity_type?: string | null;
    /** Text span [start, end] */
    span?: [number, number] | null;
    /** Correct entity type (for CORRECT_TYPE) */
    correct_type?: string | null;
    /** Correct span (for CORRECT_SPAN) */
    correct_span?: [number, number] | null;
  };
}

/**
 * Feedback response for all feedback endpoints
 */
export interface FeedbackResponse {
  /** Feedback ID */
  feedback_id: string;
  /** Status message */
  status: string;
  /** Number of training examples generated (for RLCF/NER feedback) */
  training_examples_generated?: number | null;
  /** Message */
  message: string;
}

// ============================================================================
// STATISTICS TYPES
// ============================================================================

/**
 * Feedback statistics response for GET /feedback/stats
 */
export interface FeedbackStatsResponse {
  /** Total user feedback count */
  total_user_feedback: number;
  /** Total RLCF feedback count */
  total_rlcf_feedback: number;
  /** Total NER corrections count */
  total_ner_corrections: number;
  /** Average user rating (1-5) */
  average_rating: number;
  /** Feedback breakdown by category */
  feedback_by_category: Record<string, number>;
  /** Recent feedback items */
  recent_feedback?: Array<{
    trace_id: string;
    type: 'user' | 'rlcf' | 'ner';
    timestamp: string;
  }> | null;
}

/**
 * Orchestration statistics response for GET /stats
 */
export interface OrchestrationStatsResponse {
  /** Total queries executed */
  total_queries: number;
  /** Queries by status */
  queries_by_status: Record<QueryStatus, number>;
  /** Average execution time (ms) */
  average_execution_time_ms: number;
  /** Average confidence score */
  average_confidence: number;
  /** Most common intents */
  top_intents: Array<{ intent: string; count: number }>;
  /** Most consulted experts */
  expert_usage: Record<string, number>;
  /** Agent usage statistics */
  agent_usage: Record<string, number>;
}
