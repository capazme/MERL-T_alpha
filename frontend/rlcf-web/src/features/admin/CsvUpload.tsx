import React, { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Card } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { FileUpload } from '../../components/shared/FileUpload';
import { Badge } from '../../components/ui/Badge';
import { apiClient } from '../../lib/api';

interface CsvUploadProps {
  onUploadComplete?: (tasks: any[]) => void;
}

interface UploadOptions {
  file: File;
  taskType?: string;
  maxRecords?: number;
}

const TASK_TYPES = [
  { value: '', label: 'Auto-detect' },
  { value: 'STATUTORY_RULE_QA', label: 'Statutory Rule Q&A' },
  { value: 'QA', label: 'Question Answering' },
  { value: 'CLASSIFICATION', label: 'Classification' },
  { value: 'SUMMARIZATION', label: 'Summarization' },
  { value: 'PREDICTION', label: 'Prediction' },
  { value: 'NLI', label: 'Natural Language Inference' },
  { value: 'NER', label: 'Named Entity Recognition' },
  { value: 'DRAFTING', label: 'Legal Drafting' },
  { value: 'RISK_SPOTTING', label: 'Risk Spotting' },
  { value: 'DOCTRINE_APPLICATION', label: 'Doctrine Application' },
];

export const CsvUpload: React.FC<CsvUploadProps> = ({ onUploadComplete }) => {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [taskType, setTaskType] = useState('');
  const [maxRecords, setMaxRecords] = useState<number | undefined>();
  const [previewMode, setPreviewMode] = useState(false);
  
  const queryClient = useQueryClient();

  const uploadMutation = useMutation({
    mutationFn: async (options: UploadOptions) => {
      return apiClient.tasks.uploadCsv(options.file, options.taskType);
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      onUploadComplete?.(data);
      setSelectedFile(null);
    },
  });

  const previewMutation = useMutation({
    mutationFn: async (options: UploadOptions) => {
      const blob = await apiClient.tasks.convertCsvToYaml(options.file, options.taskType, options.maxRecords);
      
      // Download the YAML file
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = selectedFile?.name?.replace('.csv', '.yaml') || 'tasks.yaml';
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    },
  });

  const handleUpload = () => {
    if (!selectedFile) return;
    
    if (previewMode) {
      previewMutation.mutate({
        file: selectedFile,
        taskType: taskType || undefined,
        maxRecords,
      });
    } else {
      uploadMutation.mutate({
        file: selectedFile,
        taskType: taskType || undefined,
      });
    }
  };

  const isLoading = uploadMutation.isPending || previewMutation.isPending;
  const error = uploadMutation.error || previewMutation.error;

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-medium text-gray-900 mb-2">
          Upload CSV Dataset
        </h3>
        <p className="text-sm text-gray-600">
          Upload a CSV file to create tasks. The system will auto-detect the task type based on column names.
        </p>
      </div>

      {/* File Upload */}
      <FileUpload
        onFileSelect={setSelectedFile}
        accept=".csv"
        maxSize={100}
      >
        {selectedFile ? (
          <div className="text-center">
            <div className="text-green-600 mb-2">
              <svg className="mx-auto h-8 w-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
            </div>
            <p className="text-sm font-medium text-gray-900">{selectedFile.name}</p>
            <p className="text-xs text-gray-500">
              {(selectedFile.size / 1024 / 1024).toFixed(2)} MB
            </p>
            <Button
              variant="outline"
              size="sm"
              onClick={(e: React.MouseEvent<HTMLButtonElement>) => {
                e.stopPropagation();
                setSelectedFile(null);
              }}
              className="mt-2"
            >
              Remove
            </Button>
          </div>
        ) : null}
      </FileUpload>

      {/* Options */}
      {selectedFile && (
        <Card className="p-4">
          <h4 className="font-medium text-gray-900 mb-4">Upload Options</h4>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Task Type */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Task Type
              </label>
              <select
                value={taskType}
                onChange={(e) => setTaskType(e.target.value)}
                className="w-full p-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              >
                {TASK_TYPES.map((type) => (
                  <option key={type.value} value={type.value}>
                    {type.label}
                  </option>
                ))}
              </select>
              {!taskType && (
                <p className="text-xs text-gray-500 mt-1">
                  System will auto-detect based on CSV columns
                </p>
              )}
            </div>

            {/* Max Records for Preview */}
            {previewMode && (
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Max Records (Preview)
                </label>
                <input
                  type="number"
                  value={maxRecords || ''}
                  onChange={(e) => setMaxRecords(e.target.value ? parseInt(e.target.value) : undefined)}
                  placeholder="All records"
                  className="w-full p-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                  min="1"
                  max="1000"
                />
              </div>
            )}
          </div>

          {/* Preview Mode Toggle */}
          <div className="mt-4">
            <label className="flex items-center">
              <input
                type="checkbox"
                checked={previewMode}
                onChange={(e) => setPreviewMode(e.target.checked)}
                className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
              />
              <span className="ml-2 text-sm text-gray-700">
                Preview mode (download YAML without creating tasks)
              </span>
            </label>
          </div>
        </Card>
      )}

      {/* Actions */}
      {selectedFile && (
        <div className="flex gap-3">
          <Button
            onClick={handleUpload}
            disabled={isLoading}
            className="flex-1"
          >
            {isLoading ? (
              <div className="flex items-center">
                <svg className="animate-spin -ml-1 mr-3 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                {previewMode ? 'Generating Preview...' : 'Uploading...'}
              </div>
            ) : (
              previewMode ? 'Download YAML Preview' : 'Upload and Create Tasks'
            )}
          </Button>
        </div>
      )}

      {/* Error Display */}
      {error && (
        <Card className="p-4 bg-red-50 border-red-200">
          <div className="flex">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="ml-3">
              <h3 className="text-sm font-medium text-red-800">Upload Error</h3>
              <p className="text-sm text-red-700 mt-1">
                {error.message}
              </p>
            </div>
          </div>
        </Card>
      )}

      {/* Success Display */}
      {uploadMutation.isSuccess && (
        <Card className="p-4 bg-green-50 border-green-200">
          <div className="flex">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-green-400" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="ml-3">
              <h3 className="text-sm font-medium text-green-800">Upload Successful</h3>
              <p className="text-sm text-green-700 mt-1">
                Created {uploadMutation.data?.length || 0} tasks successfully.
              </p>
            </div>
          </div>
        </Card>
      )}
    </div>
  );
};