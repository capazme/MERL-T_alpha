/**
 * SourceComparison - Side-by-side comparison of source text vs extracted entity
 *
 * For LLM-extracted entities from PDF documents, shows the original source
 * text alongside the extracted structured data to verify accuracy.
 */

import React from 'react';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { FileText, Database } from 'lucide-react';

// =============================================================================
// Types
// =============================================================================

interface StagingEntity {
  id: number;
  raw_data: {
    entity_type: string;
    properties: Record<string, any>;
    provenance: {
      source: string;
      source_file?: string;
      page_number?: number;
      paragraph_index?: number;
      char_start?: number;
      char_end?: number;
    };
  };
}

interface SourceComparisonProps {
  entity: StagingEntity;
}

// =============================================================================
// Helper Functions
// =============================================================================

const highlightText = (text: string, charStart?: number, charEnd?: number): string => {
  if (charStart !== undefined && charEnd !== undefined && text) {
    const before = text.substring(0, charStart);
    const highlighted = text.substring(charStart, charEnd);
    const after = text.substring(charEnd);

    return `${before}<mark class="bg-yellow-200 font-semibold">${highlighted}</mark>${after}`;
  }
  return text || '';
};

// =============================================================================
// Main Component
// =============================================================================

export const SourceComparison: React.FC<SourceComparisonProps> = ({ entity }) => {
  const { properties, provenance } = entity.raw_data;

  // Get source text (if available in properties)
  const sourceText = properties.source_text || properties.testo_completo || '';
  const extractedText = properties.text || properties.testo_completo || '';

  return (
    <Card className="bg-gray-50">
      <CardContent className="p-6">
        <div className="grid grid-cols-2 gap-6">
          {/* Source Text */}
          <div>
            <div className="flex items-center mb-3">
              <FileText className="h-5 w-5 text-blue-600 mr-2" />
              <h4 className="font-semibold text-gray-900">Original Source</h4>
            </div>

            {/* Source Metadata */}
            <div className="bg-white border border-gray-200 rounded p-3 mb-3 text-xs space-y-1">
              {provenance.source_file && (
                <div>
                  <span className="font-medium">File:</span>{' '}
                  <code className="bg-gray-100 px-1 rounded">{provenance.source_file}</code>
                </div>
              )}
              {provenance.page_number !== undefined && (
                <div>
                  <span className="font-medium">Page:</span> {provenance.page_number}
                </div>
              )}
              {provenance.paragraph_index !== undefined && (
                <div>
                  <span className="font-medium">Paragraph:</span> {provenance.paragraph_index}
                </div>
              )}
              {provenance.char_start !== undefined && provenance.char_end !== undefined && (
                <div>
                  <span className="font-medium">Characters:</span> {provenance.char_start} -{' '}
                  {provenance.char_end}
                </div>
              )}
            </div>

            {/* Source Text Display */}
            <div className="bg-white border border-gray-200 rounded p-4 max-h-96 overflow-y-auto">
              {sourceText ? (
                <div
                  className="text-sm text-gray-800 whitespace-pre-wrap"
                  dangerouslySetInnerHTML={{
                    __html: highlightText(
                      sourceText,
                      provenance.char_start,
                      provenance.char_end
                    ),
                  }}
                />
              ) : (
                <div className="text-gray-400 text-sm italic">
                  Source text not available (may have been discarded after extraction)
                </div>
              )}
            </div>
          </div>

          {/* Extracted Entity */}
          <div>
            <div className="flex items-center mb-3">
              <Database className="h-5 w-5 text-purple-600 mr-2" />
              <h4 className="font-semibold text-gray-900">Extracted Entity</h4>
            </div>

            {/* Entity Type */}
            <div className="mb-3">
              <Badge className="bg-purple-100 text-purple-800">
                {entity.raw_data.entity_type}
              </Badge>
            </div>

            {/* Extracted Properties */}
            <div className="bg-white border border-gray-200 rounded p-4 max-h-96 overflow-y-auto">
              <div className="space-y-3">
                {Object.entries(properties)
                  .filter(
                    ([key]) =>
                      !key.startsWith('import_') &&
                      !key.startsWith('brocardi_') &&
                      key !== 'source' &&
                      key !== 'source_text'
                  )
                  .map(([key, value]) => (
                    <div key={key} className="border-b border-gray-100 pb-2 last:border-0">
                      <div className="text-xs font-semibold text-gray-600 uppercase mb-1">
                        {key.replace(/_/g, ' ')}
                      </div>
                      <div className="text-sm text-gray-900">
                        {typeof value === 'string' && value.length > 300 ? (
                          <details className="cursor-pointer">
                            <summary className="text-blue-600 hover:underline text-xs">
                              {value.substring(0, 150)}... (click to expand)
                            </summary>
                            <div className="mt-2 whitespace-pre-wrap">{value}</div>
                          </details>
                        ) : typeof value === 'object' && value !== null ? (
                          <pre className="text-xs bg-gray-50 p-2 rounded overflow-x-auto">
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
          </div>
        </div>

        {/* Comparison Notes */}
        <div className="mt-4 p-3 bg-yellow-50 border border-yellow-200 rounded">
          <h5 className="font-semibold text-yellow-900 text-sm mb-1">🔍 Verification Checklist</h5>
          <ul className="text-xs text-yellow-800 space-y-1">
            <li>• Does the extracted entity accurately reflect the source text?</li>
            <li>• Are all key properties correctly extracted?</li>
            <li>• Is the entity type appropriate for this content?</li>
            <li>• Are there any missing properties that should be extracted?</li>
            <li>• Are there any hallucinated/invented properties not in source?</li>
          </ul>
        </div>
      </CardContent>
    </Card>
  );
};
