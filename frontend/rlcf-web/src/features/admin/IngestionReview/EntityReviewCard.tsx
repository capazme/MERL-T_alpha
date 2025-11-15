/**
 * EntityReviewCard - Review card for individual staging entity
 *
 * Shows entity details, confidence score, source provenance, and approve/reject actions.
 * Includes source comparison view for LLM-extracted entities.
 */

import React, { useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Textarea } from '@/components/ui/textarea';
import {
  CheckCircle,
  XCircle,
  AlertTriangle,
  ExternalLink,
  FileText,
  Database,
} from 'lucide-react';
import { SourceComparison } from './SourceComparison';

// =============================================================================
// Types
// =============================================================================

interface StagingEntity {
  id: number;
  entity_type: string;
  source_type: string;
  raw_data: {
    entity_type: string;
    properties: Record<string, any>;
    confidence: number;
    provenance: {
      source: string;
      source_url?: string;
      urn?: string;
    };
    relationships?: Array<{
      type: string;
      target_node: {
        entity_type: string;
        properties: Record<string, any>;
      };
    }>;
  };
  confidence_score: number;
  status: string;
  created_at: string;
}

interface EntityReviewCardProps {
  entity: StagingEntity;
  onApprove: (id: number, note?: string) => void;
  onReject: (id: number, note?: string) => void;
  isReviewing: boolean;
}

// =============================================================================
// Helper Functions
// =============================================================================

const getConfidenceColor = (score: number): string => {
  if (score >= 0.9) return 'text-green-600 bg-green-50';
  if (score >= 0.75) return 'text-yellow-600 bg-yellow-50';
  return 'text-red-600 bg-red-50';
};

const getSourceBadgeColor = (source: string): string => {
  const colors: Record<string, string> = {
    VISUALEX: 'bg-blue-100 text-blue-800',
    DOCUMENTS: 'bg-purple-100 text-purple-800',
    COMMUNITY: 'bg-green-100 text-green-800',
    NORMATTIVA: 'bg-orange-100 text-orange-800',
  };
  return colors[source] || 'bg-gray-100 text-gray-800';
};

// =============================================================================
// Main Component
// =============================================================================

export const EntityReviewCard: React.FC<EntityReviewCardProps> = ({
  entity,
  onApprove,
  onReject,
  isReviewing,
}) => {
  const [reviewNote, setReviewNote] = useState<string>('');
  const [showComparison, setShowComparison] = useState<boolean>(false);

  const { raw_data, confidence_score, source_type } = entity;
  const { properties, provenance, relationships } = raw_data;

  // Handle approve/reject
  const handleApprove = () => {
    onApprove(entity.id, reviewNote || undefined);
    setReviewNote('');
  };

  const handleReject = () => {
    onReject(entity.id, reviewNote || undefined);
    setReviewNote('');
  };

  return (
    <Card className="shadow-lg">
      <CardHeader className="bg-gray-50 border-b">
        <div className="flex justify-between items-start">
          <div>
            <CardTitle className="text-xl font-bold">
              {raw_data.entity_type}
              {properties.numero_articolo && ` - Art. ${properties.numero_articolo}`}
            </CardTitle>
            <div className="flex gap-2 mt-2">
              <Badge className={getSourceBadgeColor(source_type)}>{source_type}</Badge>
              <Badge className={getConfidenceColor(confidence_score)}>
                Confidence: {(confidence_score * 100).toFixed(1)}%
              </Badge>
              {confidence_score < 0.75 && (
                <Badge variant="destructive">
                  <AlertTriangle className="h-3 w-3 mr-1" />
                  Low Confidence
                </Badge>
              )}
            </div>
          </div>
          <div className="text-sm text-gray-500">
            Created: {new Date(entity.created_at).toLocaleString()}
          </div>
        </div>
      </CardHeader>

      <CardContent className="p-6 space-y-6">
        {/* Provenance Info */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <h4 className="font-semibold text-blue-900 mb-2 flex items-center">
            <Database className="h-4 w-4 mr-2" />
            Provenance
          </h4>
          <div className="grid grid-cols-2 gap-2 text-sm">
            <div>
              <span className="font-medium">Source:</span> {provenance.source}
            </div>
            {provenance.urn && (
              <div>
                <span className="font-medium">URN:</span>{' '}
                <code className="text-xs bg-white px-1 py-0.5 rounded">{provenance.urn}</code>
              </div>
            )}
            {provenance.source_url && (
              <div className="col-span-2">
                <a
                  href={provenance.source_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-600 hover:underline flex items-center"
                >
                  <ExternalLink className="h-3 w-3 mr-1" />
                  View Source
                </a>
              </div>
            )}
          </div>
        </div>

        {/* Entity Properties */}
        <div>
          <h4 className="font-semibold text-gray-900 mb-3 flex items-center">
            <FileText className="h-4 w-4 mr-2" />
            Entity Properties
          </h4>
          <div className="bg-gray-50 rounded-lg p-4 space-y-2">
            {Object.entries(properties)
              .filter(([key]) => !key.startsWith('import_') && key !== 'source')
              .map(([key, value]) => (
                <div key={key} className="flex border-b border-gray-200 pb-2 last:border-0">
                  <div className="w-1/3 font-medium text-gray-700">{key}:</div>
                  <div className="w-2/3 text-gray-900">
                    {typeof value === 'string' && value.length > 200 ? (
                      <details className="cursor-pointer">
                        <summary className="text-blue-600 hover:underline">
                          {value.substring(0, 100)}... (click to expand)
                        </summary>
                        <div className="mt-2 whitespace-pre-wrap text-sm">{value}</div>
                      </details>
                    ) : typeof value === 'object' ? (
                      <pre className="text-xs bg-white p-2 rounded overflow-x-auto">
                        {JSON.stringify(value, null, 2)}
                      </pre>
                    ) : (
                      <span>{String(value || '(empty)')}</span>
                    )}
                  </div>
                </div>
              ))}
          </div>
        </div>

        {/* Relationships (if any) */}
        {relationships && relationships.length > 0 && (
          <div>
            <h4 className="font-semibold text-gray-900 mb-3">
              Relationships ({relationships.length})
            </h4>
            <div className="space-y-2">
              {relationships.map((rel, idx) => (
                <div key={idx} className="bg-purple-50 border border-purple-200 rounded p-3">
                  <div className="font-medium text-purple-900">{rel.type}</div>
                  <div className="text-sm text-gray-700 mt-1">
                    → {rel.target_node.entity_type}:{' '}
                    {rel.target_node.properties.nome ||
                      rel.target_node.properties.testo?.substring(0, 50) ||
                      'Unnamed'}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* BrocardiInfo (if present in properties) */}
        {(properties.brocardi_ratio ||
          properties.brocardi_spiegazione ||
          properties.brocardi_position) && (
          <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
            <h4 className="font-semibold text-amber-900 mb-2">📚 BrocardiInfo</h4>
            {properties.brocardi_position && (
              <div className="text-sm mb-2">
                <span className="font-medium">Position:</span> {properties.brocardi_position}
              </div>
            )}
            {properties.brocardi_ratio && (
              <div className="text-sm mb-2">
                <span className="font-medium">Ratio:</span>{' '}
                <span className="text-gray-700">{properties.brocardi_ratio}</span>
              </div>
            )}
            {properties.brocardi_spiegazione && (
              <details className="text-sm cursor-pointer">
                <summary className="font-medium text-amber-800 hover:underline">
                  Spiegazione
                </summary>
                <div className="mt-2 text-gray-700 whitespace-pre-wrap">
                  {properties.brocardi_spiegazione}
                </div>
              </details>
            )}
          </div>
        )}

        {/* Source Comparison (for LLM-extracted entities) */}
        {source_type === 'DOCUMENTS' && (
          <div>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowComparison(!showComparison)}
              className="mb-3"
            >
              {showComparison ? 'Hide' : 'Show'} Source Comparison
            </Button>
            {showComparison && <SourceComparison entity={entity} />}
          </div>
        )}

        {/* Review Note */}
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Review Note (Optional)
          </label>
          <Textarea
            value={reviewNote}
            onChange={(e) => setReviewNote(e.target.value)}
            placeholder="Add any notes about this entity (e.g., why rejected, corrections needed)..."
            rows={3}
            className="w-full"
          />
        </div>

        {/* Action Buttons */}
        <div className="flex gap-3 pt-4 border-t">
          <Button
            onClick={handleApprove}
            disabled={isReviewing}
            className="flex-1 bg-green-600 hover:bg-green-700"
            size="lg"
          >
            {isReviewing ? (
              'Processing...'
            ) : (
              <>
                <CheckCircle className="h-5 w-5 mr-2" />
                Approve & Import to Neo4j
              </>
            )}
          </Button>

          <Button
            onClick={handleReject}
            disabled={isReviewing}
            variant="destructive"
            className="flex-1"
            size="lg"
          >
            {isReviewing ? (
              'Processing...'
            ) : (
              <>
                <XCircle className="h-5 w-5 mr-2" />
                Reject
              </>
            )}
          </Button>
        </div>

        {/* Confidence Warning */}
        {confidence_score < 0.75 && (
          <div className="bg-yellow-50 border border-yellow-300 rounded-lg p-3 flex items-start">
            <AlertTriangle className="h-5 w-5 text-yellow-600 mt-0.5 mr-2 flex-shrink-0" />
            <div className="text-sm text-yellow-800">
              <strong>Low Confidence Warning:</strong> This entity has a confidence score below
              75%. Please review carefully before approving. Consider rejecting if data quality is
              poor.
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
};
