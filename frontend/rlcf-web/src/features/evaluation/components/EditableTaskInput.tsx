import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../../../components/ui/Card';
import { Button } from '../../../components/ui/Button';
import type { LegalTask } from '../../../types/index';

interface EditableTaskInputProps {
  task: LegalTask;
  onInputChange: (updatedInputData: any) => void;
}

interface EditableFieldProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
  multiline?: boolean;
  placeholder?: string;
  icon?: string;
  required?: boolean;
}

function EditableField({ 
  label, 
  value, 
  onChange, 
  multiline = false, 
  placeholder = '', 
  icon = '',
  required = false 
}: EditableFieldProps) {
  const [isEditing, setIsEditing] = useState(false);
  const [editValue, setEditValue] = useState(value || '');

  const handleSave = () => {
    onChange(editValue);
    setIsEditing(false);
  };

  const handleCancel = () => {
    setEditValue(value || '');
    setIsEditing(false);
  };

  if (isEditing) {
    return (
      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <label className="text-sm font-medium text-slate-300">
            {icon} {label} {required && <span className="text-red-400">*</span>}
          </label>
          <div className="flex gap-2">
            <Button size="sm" onClick={handleSave} className="bg-green-600 hover:bg-green-700">
              ✓ Save
            </Button>
            <Button size="sm" variant="secondary" onClick={handleCancel}>
              ✕ Cancel
            </Button>
          </div>
        </div>
        {multiline ? (
          <textarea
            value={editValue}
            onChange={(e) => setEditValue(e.target.value)}
            placeholder={placeholder}
            className="w-full p-3 bg-slate-900 border border-blue-500 rounded-md text-slate-100 focus:ring-2 focus:ring-blue-500"
            rows={4}
            autoFocus
          />
        ) : (
          <input
            type="text"
            value={editValue}
            onChange={(e) => setEditValue(e.target.value)}
            placeholder={placeholder}
            className="w-full p-3 bg-slate-900 border border-blue-500 rounded-md text-slate-100 focus:ring-2 focus:ring-blue-500"
            autoFocus
          />
        )}
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <label className="text-sm font-medium text-slate-300">
          {icon} {label} {required && <span className="text-red-400">*</span>}
        </label>
        <Button 
          size="sm" 
          variant="ghost" 
          onClick={() => setIsEditing(true)}
          className="text-blue-400 hover:text-blue-300"
        >
          ✏️ Edit
        </Button>
      </div>
      <div className="bg-slate-800 p-3 rounded border border-slate-700 hover:border-slate-600 transition-colors">
        {value ? (
          <div className="text-slate-100 whitespace-pre-wrap">{value}</div>
        ) : (
          <div className="text-slate-400 italic">No {label.toLowerCase()} provided - click Edit to add</div>
        )}
      </div>
    </div>
  );
}

function formatEditableTaskInput(taskType: string, inputData: any, onInputChange: (field: string, value: any) => void) {
  switch (taskType) {
    case 'STATUTORY_RULE_QA':
      return (
        <div className="space-y-4">
          <EditableField
            label="Legal Question"
            value={inputData.question}
            onChange={(value) => onInputChange('question', value)}
            multiline={true}
            placeholder="Enter the legal question to be answered..."
            icon="📋"
            required={true}
          />

          <EditableField
            label="Rule ID"
            value={inputData.rule_id}
            onChange={(value) => onInputChange('rule_id', value)}
            placeholder="e.g., NORM_NORMA_DI_RIFERIMENTO_ARTICOLO_4_CODICE_PRIVACY_DEFIN"
            icon="⚖️"
          />

          <EditableField
            label="Legal Context"
            value={inputData.context_full}
            onChange={(value) => onInputChange('context_full', value)}
            multiline={true}
            placeholder="Provide the full legal context or article text..."
            icon="📚"
          />

          <EditableField
            label="Relevant Articles"
            value={inputData.relevant_articles}
            onChange={(value) => onInputChange('relevant_articles', value)}
            multiline={true}
            placeholder="List the relevant legal articles or references..."
            icon="📖"
          />

          <EditableField
            label="Category"
            value={inputData.category}
            onChange={(value) => onInputChange('category', value)}
            placeholder="e.g., Privacy, Contract Law, Criminal Law"
            icon="📂"
          />

          <EditableField
            label="Tags"
            value={inputData.tags}
            onChange={(value) => onInputChange('tags', value)}
            placeholder="e.g., Privacy; Codice In Materia Di Protezione Dei Dati Personali"
            icon="🏷️"
          />

          <div>
            <label className="text-sm font-medium text-slate-300 mb-2 block">
              🔢 Context Count
            </label>
            <input
              type="number"
              value={inputData.context_count || 1}
              onChange={(e) => onInputChange('context_count', e.target.value)}
              className="w-24 p-2 bg-slate-900 border border-slate-700 rounded text-slate-100"
              min="1"
            />
          </div>

          <EditableField
            label="Additional Metadata"
            value={typeof inputData.metadata_full === 'string' ? inputData.metadata_full : JSON.stringify(inputData.metadata_full, null, 2)}
            onChange={(value) => onInputChange('metadata_full', value)}
            multiline={true}
            placeholder="Additional structured metadata in JSON format..."
            icon="🔍"
          />
        </div>
      );

    case 'QA':
      return (
        <div className="space-y-4">
          <EditableField
            label="Question"
            value={inputData.question}
            onChange={(value) => onInputChange('question', value)}
            multiline={true}
            placeholder="Enter the question to be answered..."
            icon="❓"
            required={true}
          />

          <EditableField
            label="Context"
            value={inputData.context}
            onChange={(value) => onInputChange('context', value)}
            multiline={true}
            placeholder="Provide relevant context for answering the question..."
            icon="📄"
          />
        </div>
      );

    case 'CLASSIFICATION':
      return (
        <div className="space-y-4">
          <EditableField
            label="Text to Classify"
            value={inputData.text}
            onChange={(value) => onInputChange('text', value)}
            multiline={true}
            placeholder="Enter the text that needs to be classified..."
            icon="📝"
            required={true}
          />

          <EditableField
            label="Unit Type"
            value={inputData.unit}
            onChange={(value) => onInputChange('unit', value)}
            placeholder="e.g., case summary, document, paragraph"
            icon="📋"
          />
        </div>
      );

    case 'SUMMARIZATION':
      return (
        <div className="space-y-4">
          <EditableField
            label="Document to Summarize"
            value={inputData.document}
            onChange={(value) => onInputChange('document', value)}
            multiline={true}
            placeholder="Enter the document text that needs to be summarized..."
            icon="📄"
            required={true}
          />
        </div>
      );

    case 'PREDICTION':
      return (
        <div className="space-y-4">
          <EditableField
            label="Case Facts"
            value={inputData.facts}
            onChange={(value) => onInputChange('facts', value)}
            multiline={true}
            placeholder="Enter the facts of the case for prediction..."
            icon="⚖️"
            required={true}
          />
        </div>
      );

    case 'NLI':
      return (
        <div className="space-y-4">
          <EditableField
            label="Premise"
            value={inputData.premise}
            onChange={(value) => onInputChange('premise', value)}
            multiline={true}
            placeholder="Enter the premise statement..."
            icon="📋"
            required={true}
          />

          <EditableField
            label="Hypothesis"
            value={inputData.hypothesis}
            onChange={(value) => onInputChange('hypothesis', value)}
            multiline={true}
            placeholder="Enter the hypothesis to test against the premise..."
            icon="💭"
            required={true}
          />
        </div>
      );

    case 'NER':
      return (
        <div className="space-y-4">
          <EditableField
            label="Tokens (comma-separated)"
            value={Array.isArray(inputData.tokens) ? inputData.tokens.join(', ') : inputData.tokens}
            onChange={(value) => onInputChange('tokens', value.split(',').map(t => t.trim()))}
            multiline={true}
            placeholder="Enter tokens separated by commas..."
            icon="🏷️"
            required={true}
          />
        </div>
      );

    case 'DRAFTING':
      return (
        <div className="space-y-4">
          <EditableField
            label="Source Text"
            value={inputData.source}
            onChange={(value) => onInputChange('source', value)}
            multiline={true}
            placeholder="Enter the source text to be rewritten or improved..."
            icon="📝"
            required={true}
          />

          <EditableField
            label="Instruction"
            value={inputData.instruction}
            onChange={(value) => onInputChange('instruction', value)}
            multiline={true}
            placeholder="Provide instructions for how the text should be modified..."
            icon="📋"
            required={true}
          />
        </div>
      );

    case 'RISK_SPOTTING':
      return (
        <div className="space-y-4">
          <EditableField
            label="Text to Analyze"
            value={inputData.text}
            onChange={(value) => onInputChange('text', value)}
            multiline={true}
            placeholder="Enter the text to analyze for legal risks..."
            icon="⚠️"
            required={true}
          />
        </div>
      );

    case 'DOCTRINE_APPLICATION':
      return (
        <div className="space-y-4">
          <EditableField
            label="Facts"
            value={inputData.facts}
            onChange={(value) => onInputChange('facts', value)}
            multiline={true}
            placeholder="Enter the factual scenario..."
            icon="📄"
            required={true}
          />

          <EditableField
            label="Legal Question"
            value={inputData.question}
            onChange={(value) => onInputChange('question', value)}
            multiline={true}
            placeholder="Enter the legal question to be answered..."
            icon="❓"
            required={true}
          />
        </div>
      );

    default:
      return (
        <div className="space-y-4">
          <EditableField
            label="Raw Input Data (JSON)"
            value={JSON.stringify(inputData, null, 2)}
            onChange={(value) => {
              try {
                const parsed = JSON.parse(value);
                Object.keys(parsed).forEach(key => onInputChange(key, parsed[key]));
              } catch (e) {
                // Invalid JSON, ignore for now
              }
            }}
            multiline={true}
            placeholder="Enter valid JSON..."
            icon="🔧"
          />
        </div>
      );
  }
}

export function EditableTaskInput({ task, onInputChange }: EditableTaskInputProps) {
  const [inputData, setInputData] = useState(task.input_data);
  const [hasChanges, setHasChanges] = useState(false);

  const handleFieldChange = (field: string, value: any) => {
    const updatedData = { ...inputData, [field]: value };
    setInputData(updatedData);
    setHasChanges(true);
  };

  const handleSaveAll = () => {
    onInputChange(inputData);
    setHasChanges(false);
  };

  const handleResetAll = () => {
    setInputData(task.input_data);
    setHasChanges(false);
  };

  return (
    <Card className="border-slate-700">
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            ✏️ Editable Task Input
            <span className="text-sm font-normal bg-slate-700 px-2 py-1 rounded">
              {task.task_type}
            </span>
          </div>
          {hasChanges && (
            <div className="flex gap-2">
              <Button size="sm" onClick={handleSaveAll} className="bg-green-600 hover:bg-green-700">
                💾 Save All Changes
              </Button>
              <Button size="sm" variant="secondary" onClick={handleResetAll}>
                🔄 Reset
              </Button>
            </div>
          )}
        </CardTitle>
        {hasChanges && (
          <div className="text-sm text-orange-400 bg-orange-900/20 px-3 py-2 rounded border border-orange-700">
            ⚠️ You have unsaved changes to the task input
          </div>
        )}
      </CardHeader>
      <CardContent>
        {formatEditableTaskInput(task.task_type, inputData, handleFieldChange)}
      </CardContent>
    </Card>
  );
}