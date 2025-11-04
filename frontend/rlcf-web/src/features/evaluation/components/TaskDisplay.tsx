import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../../../components/ui/Card';
import type { LegalTask, Response } from '../../../types/index';
import { cn } from '@/lib/utils';

interface TaskDisplayProps {
  task: LegalTask;
  mode: 'standard' | 'preference';
  responseA: Response;
  responseB?: Response | null;
}

function ReadOnlyField({ label, value, icon, isCode = false }: { label: string; value: React.ReactNode; icon: string; isCode?: boolean }) {
  return (
    <div>
      <div className="text-sm font-medium text-slate-400 flex items-center gap-2 mb-1">{icon} {label}</div>
      <div className={cn(
        "text-slate-200 bg-slate-900/70 p-3 rounded border border-slate-700",
        isCode ? 'font-mono text-xs' : 'whitespace-pre-wrap'
      )}>
        {value || <span className="italic text-slate-500">Not provided</span>}
      </div>
    </div>
  );
}

function formatTaskInput(taskType: string, inputData: any) {
  switch (taskType) {
    case 'QA':
      return (
        <div className="space-y-4">
          <ReadOnlyField label="Question" value={inputData.question} icon="❓" />
          <ReadOnlyField label="Context" value={inputData.context} icon="📄" />
        </div>
      );
    case 'STATUTORY_RULE_QA':
      return (
        <div className="space-y-4">
          <ReadOnlyField label="Legal Question" value={inputData.question} icon="📋" />
          <ReadOnlyField label="Rule ID" value={inputData.rule_id} icon="⚖️" isCode />
          <ReadOnlyField label="Legal Context" value={inputData.context_full} icon="📚" />
          <ReadOnlyField label="Relevant Articles" value={inputData.relevant_articles} icon="📖" />
        </div>
      );
    case 'CLASSIFICATION':
      return (
        <div className="space-y-4">
          <ReadOnlyField label="Text to Classify" value={inputData.text} icon="📝" />
          <ReadOnlyField label="Unit Type" value={inputData.unit} icon="📋" />
        </div>
      );
    case 'SUMMARIZATION':
      return <ReadOnlyField label="Document to Summarize" value={inputData.document} icon="📄" />;
    default:
      return <ReadOnlyField label="Raw Input Data" value={JSON.stringify(inputData, null, 2)} icon="🔧" isCode />;
  }
}

function AIResponseCard({ response, title, borderColor }: { response: Response; title: string; borderColor: string }) {
  return (
    <Card className={cn('border-slate-700 bg-gradient-to-br from-slate-800/50 to-slate-900/50', borderColor)}>
      <CardHeader className="pb-3">
        <CardTitle className="text-lg flex items-center justify-between">
          <span>{title}</span>
          {response.model_version && (
            <span className="text-sm font-normal bg-slate-700 px-2 py-1 rounded">
              {response.model_version}
            </span>
          )}
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="text-slate-200 bg-slate-900 p-4 rounded border border-slate-700 whitespace-pre-wrap min-h-[100px]">
          {response.output_data?.response_text || JSON.stringify(response.output_data, null, 2)}
        </div>
      </CardContent>
    </Card>
  );
}

export function TaskDisplay({ task, mode, responseA, responseB }: TaskDisplayProps) {
  return (
    <div className="space-y-6">
      <Card variant="gradient" className="border-violet-500/30">
        <CardHeader className="flex-row items-center justify-between">
            <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-violet-900/50 ring-1 ring-violet-500/30">
                    <span className="text-xl">📋</span>
                </div>
                <div>
                    <CardTitle className="text-lg">Task Input</CardTitle>
                    <p className="text-sm text-slate-400">{task.task_type}</p>
                </div>
            </div>
        </CardHeader>
        <CardContent>
          {formatTaskInput(task.task_type, task.input_data)}
        </CardContent>
      </Card>

      {mode === 'standard' ? (
        <AIResponseCard response={responseA} title="🤖 Response to Evaluate" borderColor="border-transparent" />
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <AIResponseCard response={responseA} title="Response A" borderColor="border-blue-500" />
          {responseB && <AIResponseCard response={responseB} title="Response B" borderColor="border-green-500" />}
        </div>
      )}
    </div>
  );
}