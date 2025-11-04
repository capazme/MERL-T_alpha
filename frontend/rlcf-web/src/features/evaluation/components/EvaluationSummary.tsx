import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../../../components/ui/Card';

interface EvaluationSummaryProps {
  taskType: string;
  formData: any;
  scores: {
    accuracy: number;
    utility: number;
    transparency: number;
  };
  isDevilsAdvocate?: boolean;
}

function formatFormData(taskType: string, data: any) {
  switch (taskType) {
    case 'QA':
      return (
        <div className="space-y-3">
          <div>
            <div className="text-sm font-medium text-slate-300">Validated Answer</div>
            <div className="text-slate-100 bg-slate-800 p-3 rounded mt-1">
              {data.validated_answer || 'Not provided'}
            </div>
          </div>
          <div>
            <div className="text-sm font-medium text-slate-300">Position</div>
            <span className={`inline-block px-2 py-1 rounded text-xs font-medium ${
              data.position === 'correct' 
                ? 'bg-green-500/20 text-green-400' 
                : 'bg-red-500/20 text-red-400'
            }`}>
              {data.position || 'Not selected'}
            </span>
          </div>
          <div>
            <div className="text-sm font-medium text-slate-300">Reasoning</div>
            <div className="text-slate-200 bg-slate-800/50 p-3 rounded mt-1 text-sm">
              {data.reasoning || 'No reasoning provided'}
            </div>
          </div>
        </div>
      );

    case 'STATUTORY_RULE_QA':
      return (
        <div className="space-y-4">
          <div>
            <div className="text-sm font-medium text-slate-300">⚖️ Validated Legal Answer</div>
            <div className="text-slate-100 bg-slate-800 p-3 rounded mt-1 border-l-4 border-purple-500">
              {data.validated_answer || 'Not provided'}
            </div>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <div className="text-sm font-medium text-slate-300">Overall Position</div>
              <span className={`inline-block px-2 py-1 rounded text-xs font-medium ${
                data.position === 'correct' 
                  ? 'bg-green-500/20 text-green-400' 
                  : 'bg-red-500/20 text-red-400'
              }`}>
                {data.position || 'Not selected'}
              </span>
            </div>
            
            <div>
              <div className="text-sm font-medium text-slate-300">Legal Accuracy</div>
              <span className={`inline-block px-2 py-1 rounded text-xs font-medium ${
                data.legal_accuracy === 'accurate' ? 'bg-green-500/20 text-green-400' :
                data.legal_accuracy === 'partially_accurate' ? 'bg-yellow-500/20 text-yellow-400' :
                data.legal_accuracy === 'inaccurate' ? 'bg-red-500/20 text-red-400' :
                'bg-slate-500/20 text-slate-400'
              }`}>
                {data.legal_accuracy || 'Not assessed'}
              </span>
            </div>
            
            <div>
              <div className="text-sm font-medium text-slate-300">Citation Quality</div>
              <span className={`inline-block px-2 py-1 rounded text-xs font-medium ${
                data.citation_quality === 'excellent' ? 'bg-green-500/20 text-green-400' :
                data.citation_quality === 'good' ? 'bg-blue-500/20 text-blue-400' :
                data.citation_quality === 'fair' ? 'bg-yellow-500/20 text-yellow-400' :
                data.citation_quality === 'poor' ? 'bg-red-500/20 text-red-400' :
                'bg-slate-500/20 text-slate-400'
              }`}>
                {data.citation_quality || 'Not rated'}
              </span>
            </div>
          </div>
          
          <div>
            <div className="text-sm font-medium text-slate-300">Legal Reasoning</div>
            <div className="text-slate-200 bg-slate-800/50 p-3 rounded mt-1 text-sm border-l-4 border-purple-500">
              {data.reasoning || 'No reasoning provided'}
            </div>
          </div>
        </div>
      );

    case 'CLASSIFICATION':
      return (
        <div className="space-y-3">
          <div>
            <div className="text-sm font-medium text-slate-300">Validated Labels</div>
            <div className="flex flex-wrap gap-1 mt-1">
              {(data.validated_labels || []).map((label: string, idx: number) => (
                <span key={idx} className="bg-blue-500/20 text-blue-400 px-2 py-1 rounded text-xs">
                  {label}
                </span>
              ))}
              {(!data.validated_labels || data.validated_labels.length === 0) && (
                <span className="text-slate-400 text-sm">No labels provided</span>
              )}
            </div>
          </div>
          <div>
            <div className="text-sm font-medium text-slate-300">Reasoning</div>
            <div className="text-slate-200 bg-slate-800/50 p-3 rounded mt-1 text-sm">
              {data.reasoning || 'No reasoning provided'}
            </div>
          </div>
        </div>
      );

    case 'SUMMARIZATION':
      return (
        <div className="space-y-3">
          <div>
            <div className="text-sm font-medium text-slate-300">Revised Summary</div>
            <div className="text-slate-100 bg-slate-800 p-3 rounded mt-1">
              {data.revised_summary || 'Not provided'}
            </div>
          </div>
          <div>
            <div className="text-sm font-medium text-slate-300">Rating</div>
            <span className={`inline-block px-2 py-1 rounded text-xs font-medium ${
              data.rating === 'good' 
                ? 'bg-green-500/20 text-green-400' 
                : 'bg-red-500/20 text-red-400'
            }`}>
              {data.rating || 'Not rated'}
            </span>
          </div>
          <div>
            <div className="text-sm font-medium text-slate-300">Reasoning</div>
            <div className="text-slate-200 bg-slate-800/50 p-3 rounded mt-1 text-sm">
              {data.reasoning || 'No reasoning provided'}
            </div>
          </div>
        </div>
      );

    case 'PREDICTION':
      return (
        <div className="space-y-3">
          <div>
            <div className="text-sm font-medium text-slate-300">Chosen Outcome</div>
            <span className={`inline-block px-2 py-1 rounded text-xs font-medium ${
              data.chosen_outcome === 'violation' 
                ? 'bg-red-500/20 text-red-400' 
                : 'bg-green-500/20 text-green-400'
            }`}>
              {data.chosen_outcome || 'Not selected'}
            </span>
          </div>
          <div>
            <div className="text-sm font-medium text-slate-300">Reasoning</div>
            <div className="text-slate-200 bg-slate-800/50 p-3 rounded mt-1 text-sm">
              {data.reasoning || 'No reasoning provided'}
            </div>
          </div>
        </div>
      );

    case 'NLI':
      return (
        <div className="space-y-3">
          <div>
            <div className="text-sm font-medium text-slate-300">Chosen Label</div>
            <span className={`inline-block px-2 py-1 rounded text-xs font-medium ${
              data.chosen_label === 'entail' ? 'bg-green-500/20 text-green-400' :
              data.chosen_label === 'contradict' ? 'bg-red-500/20 text-red-400' :
              'bg-yellow-500/20 text-yellow-400'
            }`}>
              {data.chosen_label || 'Not selected'}
            </span>
          </div>
          <div>
            <div className="text-sm font-medium text-slate-300">Reasoning</div>
            <div className="text-slate-200 bg-slate-800/50 p-3 rounded mt-1 text-sm">
              {data.reasoning || 'No reasoning provided'}
            </div>
          </div>
        </div>
      );

    case 'NER':
      return (
        <div className="space-y-3">
          <div>
            <div className="text-sm font-medium text-slate-300">Validated Tags</div>
            <div className="flex flex-wrap gap-1 mt-1">
              {(data.validated_tags || []).map((tag: string, idx: number) => (
                <span key={idx} className="bg-yellow-500/20 text-yellow-400 px-2 py-1 rounded text-xs">
                  {tag}
                </span>
              ))}
              {(!data.validated_tags || data.validated_tags.length === 0) && (
                <span className="text-slate-400 text-sm">No tags provided</span>
              )}
            </div>
          </div>
          <div>
            <div className="text-sm font-medium text-slate-300">Reasoning</div>
            <div className="text-slate-200 bg-slate-800/50 p-3 rounded mt-1 text-sm">
              {data.reasoning || 'No reasoning provided'}
            </div>
          </div>
        </div>
      );

    case 'DRAFTING':
      return (
        <div className="space-y-3">
          <div>
            <div className="text-sm font-medium text-slate-300">Revised Target</div>
            <div className="text-slate-100 bg-slate-800 p-3 rounded mt-1">
              {data.revised_target || 'Not provided'}
            </div>
          </div>
          <div>
            <div className="text-sm font-medium text-slate-300">Rating</div>
            <span className={`inline-block px-2 py-1 rounded text-xs font-medium ${
              data.rating === 'better' 
                ? 'bg-green-500/20 text-green-400' 
                : 'bg-red-500/20 text-red-400'
            }`}>
              {data.rating || 'Not rated'}
            </span>
          </div>
          <div>
            <div className="text-sm font-medium text-slate-300">Reasoning</div>
            <div className="text-slate-200 bg-slate-800/50 p-3 rounded mt-1 text-sm">
              {data.reasoning || 'No reasoning provided'}
            </div>
          </div>
        </div>
      );

    case 'RISK_SPOTTING':
      return (
        <div className="space-y-3">
          <div>
            <div className="text-sm font-medium text-slate-300">Validated Risk Labels</div>
            <div className="flex flex-wrap gap-1 mt-1">
              {(data.validated_risk_labels || []).map((label: string, idx: number) => (
                <span key={idx} className="bg-red-500/20 text-red-400 px-2 py-1 rounded text-xs">
                  {label}
                </span>
              ))}
              {(!data.validated_risk_labels || data.validated_risk_labels.length === 0) && (
                <span className="text-slate-400 text-sm">No risk labels provided</span>
              )}
            </div>
          </div>
          <div>
            <div className="text-sm font-medium text-slate-300">Validated Severity</div>
            <div className="flex items-center gap-2 mt-1">
              <div className="flex-1 bg-slate-700 rounded-full h-2">
                <div 
                  className={`h-2 rounded-full transition-all ${
                    (data.validated_severity || 0) <= 3 ? 'bg-green-500' :
                    (data.validated_severity || 0) <= 6 ? 'bg-yellow-500' :
                    'bg-red-500'
                  }`}
                  style={{ width: `${((data.validated_severity || 0) / 10) * 100}%` }}
                />
              </div>
              <span className="text-sm text-slate-300">{data.validated_severity || 0}/10</span>
            </div>
          </div>
          <div>
            <div className="text-sm font-medium text-slate-300">Reasoning</div>
            <div className="text-slate-200 bg-slate-800/50 p-3 rounded mt-1 text-sm">
              {data.reasoning || 'No reasoning provided'}
            </div>
          </div>
        </div>
      );

    case 'DOCTRINE_APPLICATION':
      return (
        <div className="space-y-3">
          <div>
            <div className="text-sm font-medium text-slate-300">Chosen Label</div>
            <span className={`inline-block px-2 py-1 rounded text-xs font-medium ${
              data.chosen_label === 'yes' 
                ? 'bg-green-500/20 text-green-400' 
                : 'bg-red-500/20 text-red-400'
            }`}>
              {data.chosen_label || 'Not selected'}
            </span>
          </div>
          <div>
            <div className="text-sm font-medium text-slate-300">Reasoning</div>
            <div className="text-slate-200 bg-slate-800/50 p-3 rounded mt-1 text-sm">
              {data.reasoning || 'No reasoning provided'}
            </div>
          </div>
        </div>
      );

    default:
      return (
        <div className="bg-slate-800 p-3 rounded">
          <pre className="text-xs text-slate-200 overflow-auto">
            {JSON.stringify(data, null, 2)}
          </pre>
        </div>
      );
  }
}

export function EvaluationSummary({ taskType, formData, scores, isDevilsAdvocate }: EvaluationSummaryProps) {
  const averageScore = (scores.accuracy + scores.utility + scores.transparency) / 3;
  
  return (
    <div className="space-y-6">
      {/* Quality Scores Summary */}
      <Card className="border-slate-700">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            📊 Quality Scores Summary
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="text-center">
              <div className="text-2xl font-bold text-blue-400">{scores.accuracy}</div>
              <div className="text-sm text-slate-400">Accuracy</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-purple-400">{scores.utility}</div>
              <div className="text-sm text-slate-400">Utility</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-cyan-400">{scores.transparency}</div>
              <div className="text-sm text-slate-400">Transparency</div>
            </div>
            <div className="text-center border-l border-slate-700">
              <div className="text-2xl font-bold text-green-400">{averageScore.toFixed(1)}</div>
              <div className="text-sm text-slate-400">Average</div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Form Data Summary */}
      <Card className="border-slate-700">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            📝 Your Evaluation
          </CardTitle>
        </CardHeader>
        <CardContent>
          {formatFormData(taskType, formData)}
        </CardContent>
      </Card>

      {/* Devil's Advocate Summary */}
      {isDevilsAdvocate && formData.devils_advocate && (
        <Card className="border-red-700 bg-red-950/20">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-red-400">
              😈 Devil's Advocate Analysis
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div>
              <div className="text-sm font-medium text-slate-300">Critical Findings</div>
              <div className="text-slate-200 bg-red-900/20 p-3 rounded mt-1 text-sm border-l-4 border-red-500">
                {formData.devils_advocate.critical_findings || 'No critical findings provided'}
              </div>
            </div>
            {formData.devils_advocate.alternative_positions && formData.devils_advocate.alternative_positions.length > 0 && (
              <div>
                <div className="text-sm font-medium text-slate-300">Alternative Positions</div>
                <div className="flex flex-wrap gap-1 mt-1">
                  {formData.devils_advocate.alternative_positions.map((position: string, idx: number) => (
                    <span key={idx} className="bg-red-500/20 text-red-400 px-2 py-1 rounded text-xs">
                      {position}
                    </span>
                  ))}
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}