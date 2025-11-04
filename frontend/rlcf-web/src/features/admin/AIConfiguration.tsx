import React, { useState, useEffect } from 'react';
import { Card } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { apiClient } from '../../lib/api';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';

interface AIModel {
  id: string;
  name: string;
  description: string;
  recommended_for: string[];
}

interface AIConfig {
  apiKey: string;
  selectedModel: string;
  temperature: number;
  maxTokens: number;
}

export const AIConfiguration: React.FC = () => {
  const [testResult, setTestResult] = useState<any>(null);
  const [showApiKey, setShowApiKey] = useState(false);
  const queryClient = useQueryClient();

  // Fetch AI configuration from backend
  const { data: savedConfig, isLoading: loadingConfig } = useQuery({
    queryKey: ['ai-config'],
    queryFn: () => apiClient.ai.getConfig(),
    retry: 2,
  });

  // Local state for editing
  const [config, setConfig] = useState<AIConfig>({
    apiKey: '',
    selectedModel: 'openai/gpt-3.5-turbo',
    temperature: 0.7,
    maxTokens: 1000,
  });

  // Initialize config from backend
  useEffect(() => {
    if (savedConfig) {
      setConfig({
        apiKey: savedConfig.api_key || '',
        selectedModel: savedConfig.selected_model || 'openai/gpt-3.5-turbo',
        temperature: savedConfig.temperature || 0.7,
        maxTokens: savedConfig.max_tokens || 1000,
      });
    }
  }, [savedConfig]);

  const { data: modelsData, isLoading: modelsLoading } = useQuery({
    queryKey: ['ai-models'],
    queryFn: () => apiClient.ai.getModels(),
  });

  // Save config mutation
  const saveConfigMutation = useMutation({
    mutationFn: (aiConfig: AIConfig) => apiClient.ai.updateConfig({
      api_key: aiConfig.apiKey,
      selected_model: aiConfig.selectedModel,
      temperature: aiConfig.temperature,
      max_tokens: aiConfig.maxTokens,
    }),
    onMutate: () => {
      toast.loading('Saving AI configuration...', { id: 'save-ai-config' });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['ai-config'] });
      toast.success('AI configuration saved successfully! ✅', {
        id: 'save-ai-config',
        description: 'Your AI model settings have been updated.'
      });
    },
    onError: (error: any) => {
      toast.error('Failed to save AI configuration', {
        id: 'save-ai-config',
        description: error.message || 'Please try again.'
      });
    },
  });

  const testMutation = useMutation({
    mutationFn: async () => {
      const testRequest = {
        task_type: 'QA',
        input_data: {
          question: 'What is a contract?',
          context: 'Legal contracts are agreements between parties.'
        },
        model_config: {
          name: config.selectedModel,
          api_key: config.apiKey,
          temperature: config.temperature,
          max_tokens: config.maxTokens,
        }
      };
      return apiClient.ai.generateResponse(testRequest);
    },
    onMutate: () => {
      setTestResult(null);
      toast.loading('Testing AI connection...', { id: 'test-ai' });
    },
    onSuccess: (data) => {
      setTestResult({ success: true, data });
      toast.success('AI connection test successful! ✅', {
        id: 'test-ai',
        description: 'The AI model responded correctly.'
      });
    },
    onError: (error: any) => {
      setTestResult({ success: false, error: error.message });
      toast.error('AI connection test failed', {
        id: 'test-ai',
        description: error.message || 'Please check your API key and model selection.'
      });
    },
  });

  // Reset to defaults mutation
  const resetToDefaultsMutation = useMutation({
    mutationFn: () => apiClient.ai.getDefaults(),
    onSuccess: (defaults) => {
      setConfig({
        apiKey: defaults.api_key || '',
        selectedModel: defaults.selected_model || 'openai/gpt-3.5-turbo',
        temperature: defaults.temperature || 0.7,
        maxTokens: defaults.max_tokens || 1000,
      });
      toast.success('Reset to default configuration', {
        description: 'AI settings have been reset to defaults.'
      });
    },
    onError: () => {
      toast.error('Failed to load defaults');
    },
  });

  const models = modelsData?.models || [];

  return (
    <div className="space-y-6">
      <Card className="p-6">
        <h3 className="text-lg font-semibold text-white mb-4">AI Model Configuration</h3>
        
        <div className="space-y-4">
          {/* API Key */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              OpenRouter API Key
            </label>
            <div className="flex gap-2">
              <input
                type={showApiKey ? 'text' : 'password'}
                value={config.apiKey}
                onChange={(e) => setConfig(prev => ({ ...prev, apiKey: e.target.value }))}
                placeholder="sk-or-..."
                className="flex-1 px-3 py-2 bg-slate-800 border border-slate-600 rounded-md text-white placeholder-gray-400"
              />
              <Button
                variant="outline"
                onClick={() => setShowApiKey(!showApiKey)}
              >
                {showApiKey ? 'Hide' : 'Show'}
              </Button>
            </div>
            <p className="text-xs text-gray-400 mt-1">
              Get your API key from <a href="https://openrouter.ai/keys" target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:underline">openrouter.ai/keys</a>
            </p>
          </div>

          {/* Model Selection */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              AI Model
            </label>
            <select
              value={config.selectedModel}
              onChange={(e) => setConfig(prev => ({ ...prev, selectedModel: e.target.value }))}
              className="w-full px-3 py-2 bg-slate-800 border border-slate-600 rounded-md text-white"
              disabled={modelsLoading}
            >
              {models.map((model: AIModel) => (
                <option key={model.id} value={model.id}>
                  {model.name} - {model.description}
                </option>
              ))}
            </select>
            {config.selectedModel && (
              <div className="mt-2 p-2 bg-slate-900 rounded text-xs text-gray-300">
                <strong>Recommended for:</strong> {
                  models.find((m: AIModel) => m.id === config.selectedModel)?.recommended_for?.join(', ') || 'General tasks'
                }
              </div>
            )}
          </div>

          {/* Temperature */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Temperature: {config.temperature}
            </label>
            <input
              type="range"
              min="0"
              max="2"
              step="0.1"
              value={config.temperature}
              onChange={(e) => setConfig(prev => ({ ...prev, temperature: parseFloat(e.target.value) }))}
              className="w-full"
            />
            <div className="flex justify-between text-xs text-gray-400 mt-1">
              <span>More focused</span>
              <span>More creative</span>
            </div>
          </div>

          {/* Max Tokens */}
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Max Tokens
            </label>
            <input
              type="number"
              min="100"
              max="4000"
              step="100"
              value={config.maxTokens}
              onChange={(e) => setConfig(prev => ({ ...prev, maxTokens: parseInt(e.target.value) }))}
              className="w-full px-3 py-2 bg-slate-800 border border-slate-600 rounded-md text-white"
            />
            <p className="text-xs text-gray-400 mt-1">
              Maximum length of AI response (100-4000 tokens)
            </p>
          </div>

          {/* Actions */}
          <div className="flex gap-2 pt-4">
            <Button
              onClick={() => saveConfigMutation.mutate(config)}
              disabled={saveConfigMutation.isPending}
            >
              {saveConfigMutation.isPending ? 'Saving...' : 'Save Configuration'}
            </Button>
            <Button
              variant="outline"
              onClick={() => testMutation.mutate()}
              disabled={!config.apiKey || testMutation.isPending}
            >
              {testMutation.isPending ? 'Testing...' : 'Test AI Connection'}
            </Button>
            <Button
              variant="outline"
              onClick={() => resetToDefaultsMutation.mutate()}
              disabled={resetToDefaultsMutation.isPending}
            >
              {resetToDefaultsMutation.isPending ? 'Resetting...' : 'Reset to Defaults'}
            </Button>
          </div>
        </div>
      </Card>

      {/* Test Results */}
      {testResult && (
        <Card className="p-4">
          <h4 className="text-md font-medium text-white mb-2">Test Results</h4>
          {testResult.success ? (
            <div className="space-y-2">
              <div className="text-green-400 text-sm">✓ AI connection successful!</div>
              <div className="bg-slate-900 p-3 rounded text-xs">
                <div className="text-gray-400 mb-1">Response:</div>
                <div className="text-white">{testResult.data?.response_data?.response_text || 'No response text'}</div>
                <div className="text-gray-400 mt-2 text-xs">
                  Model: {testResult.data?.model_used} | 
                  Confidence: {testResult.data?.response_data?.confidence || 'N/A'}
                </div>
              </div>
            </div>
          ) : (
            <div className="space-y-2">
              <div className="text-red-400 text-sm">✗ AI connection failed</div>
              <div className="bg-red-900/20 p-3 rounded text-xs text-red-300">
                {testResult.error}
              </div>
            </div>
          )}
        </Card>
      )}

      {/* Usage Instructions */}
      <Card className="p-4">
        <h4 className="text-md font-medium text-white mb-2">Setup Instructions</h4>
        <div className="text-sm text-gray-300 space-y-2">
          <p>1. Get an API key from <a href="https://openrouter.ai/keys" target="_blank" rel="noopener noreferrer" className="text-blue-400 hover:underline">OpenRouter</a></p>
          <p>2. Choose an AI model based on your task requirements</p>
          <p>3. Adjust temperature (0.0 = focused, 2.0 = creative)</p>
          <p>4. Set max tokens based on desired response length</p>
          <p>5. Test the connection to verify everything works</p>
          <p className="text-yellow-400 text-xs mt-3">
            <strong>Note:</strong> In production, API keys should be configured server-side with environment variables for security.
          </p>
        </div>
      </Card>
    </div>
  );
};