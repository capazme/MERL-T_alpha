/**
 * Query Submission Page
 *
 * Main page for submitting legal queries to the MERL-T orchestration layer.
 *
 * PLACEHOLDER: Will be fully implemented in Phase 2.
 */

import { Card, CardHeader, CardTitle, CardContent } from '@components/ui/Card';
import { Search } from 'lucide-react';

export function QuerySubmission() {
  return (
    <div className="max-w-6xl mx-auto p-6">
      <div className="mb-6">
        <h1 className="text-3xl font-bold text-white flex items-center gap-3">
          <Search className="w-8 h-8 text-blue-400" />
          Legal Query
        </h1>
        <p className="text-gray-400 mt-2">
          Submit a legal question and get AI-powered answers from MERL-T
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Query Submission Interface</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center py-12">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-blue-500/20 mb-4">
              <Search className="w-8 h-8 text-blue-400" />
            </div>
            <h3 className="text-xl font-semibold text-white mb-2">
              Coming Soon
            </h3>
            <p className="text-gray-400 max-w-md mx-auto">
              The query submission interface is being implemented in Phase 2.
              This will include query input, context configuration, and execution options.
            </p>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
