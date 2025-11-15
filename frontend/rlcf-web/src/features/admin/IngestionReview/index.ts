/**
 * Ingestion Review Components - Admin UI for staging queue review
 *
 * This module provides the complete UI for reviewing entities from the
 * multi-source ingestion pipeline before they are imported to Neo4j.
 *
 * Features:
 * - Staging entity list with filters (source, status, confidence)
 * - Individual entity review cards with approve/reject actions
 * - Confidence score distribution visualization
 * - Source comparison for LLM-extracted entities
 * - Batch approval operations
 *
 * Usage:
 *   import { StagingEntityList } from '@/features/admin/IngestionReview';
 *
 *   // In your admin routes
 *   <Route path="/admin/ingestion-review" element={<StagingEntityList />} />
 */

export { StagingEntityList } from './StagingEntityList';
export { EntityReviewCard } from './EntityReviewCard';
export { ConfidenceScoreChart } from './ConfidenceScoreChart';
export { SourceComparison } from './SourceComparison';
