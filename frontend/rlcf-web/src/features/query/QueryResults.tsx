/**
 * Query Results Page
 *
 * Displays legal query results with answer, provenance, and feedback options.
 *
 * PLACEHOLDER: Will be fully implemented in Phase 3.
 */

import { useParams } from 'react-router-dom';
import { Card, CardHeader, CardTitle, CardContent } from '@components/ui/Card';
import { FileText } from 'lucide-react';

export function QueryResults() {
  const { traceId } = useParams<{ traceId: string }>();

  return (
    <div className="max-w-6xl mx-auto p-6">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-white flex items-center gap-3">
          <FileText className="w-8 h-8 text-green-400" />
          Query Results
        </h1>
        <p className="text-gray-400 mt-2">
          Trace ID: {traceId}
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Results Display Interface</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center py-12">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-green-500/20 mb-4">
              <FileText className="w-8 h-8 text-green-400" />
            </div>
            <h3 className="text-xl font-semibold text-white mb-2">
              Coming Soon
            </h3>
            <p className="text-gray-400 max-w-md mx-auto">
              The results display interface is being implemented in Phase 3.
              This will include the answer, legal basis, jurisprudence, provenance trace, and feedback options.
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
