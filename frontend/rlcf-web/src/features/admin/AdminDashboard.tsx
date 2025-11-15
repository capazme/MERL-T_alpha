import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { Card, CardContent, CardHeader, CardTitle } from '@components/ui/Card';
import { Button } from '@components/ui/Button';
import { Badge } from '@components/ui/Badge';
import { useTasks, useUsers, useCreateTask, useBatchCreateTasksFromYaml, useCreateUser, useAddCredential, useModelConfig, useTaskConfig, useUpdateModelConfig, useUpdateTaskConfig, useSetApiKey, useUpdateTaskStatus, useExportDataset } from '@hooks/useApi';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/lib/api';
import type { LegalTask, User, TaskType } from '@/types/index';
import { RefreshCw, Download, Upload, Users, CheckCircle, Clock, BarChart, Database } from 'lucide-react';
import { toast } from 'sonner';
import { TaskManager } from './TaskManager';
import { CsvUpload } from './CsvUpload';
import { AIConfiguration } from './AIConfiguration';

const taskInputPlaceholders: Record<string, string> = {
  QA: JSON.stringify({ question: "What is the statute of limitations for breach of contract?", context: "The contract was signed on Jan 1, 2020." }, null, 2),
  STATUTORY_RULE_QA: JSON.stringify({ 
    id: "Q201923077", 
    question: "Ciao! La mia è una domanda semplice: ma sono legali i sistemi di riconoscimento biometrico per il controllo accessi aziendali?", 
    rule_id: "NORM_NORMA_DI_RIFERIMENTO_ARTICOLO_4_CODICE_PRIVACY_DEFIN", 
    context_full: "[Art.1: title: Articolo 4 Codice In Materia Di Protezione Dei Dati Personali]", 
    context_count: 1, 
    relevant_articles: "Norma di riferimento:Articolo 4 Codice privacy", 
    tags: "Privacy; Codice In Materia Di Protezione Dei Dati Personali", 
    category: "Privacy" 
  }, null, 2),
  CLASSIFICATION: JSON.stringify({ text: "The defendant failed to deliver the goods as per the agreement.", unit: "case summary" }, null, 2),
  SUMMARIZATION: JSON.stringify({ document: "A long legal document text..." }, null, 2),
  PREDICTION: JSON.stringify({ facts: "The plaintiff has a strong case with clear evidence." }, null, 2),
  NLI: JSON.stringify({ premise: "The agreement was signed by both parties.", hypothesis: "A valid contract exists." }, null, 2),
  NER: JSON.stringify({ tokens: ["John", "Doe", "vs", "ACME", "Corp"] }, null, 2),
  DRAFTING: JSON.stringify({ source: "The party of the first part...", instruction: "Rewrite this clause in plain English." }, null, 2),
  RISK_SPOTTING: JSON.stringify({ text: "The company stores user data without explicit consent." }, null, 2),
  DOCTRINE_APPLICATION: JSON.stringify({ facts: "The defendant acted in self-defense.", question: "Is the use of force justified?" }, null, 2),
};

type AdminView = 'dashboard' | 'tasks' | 'upload' | 'ai-config';

export function AdminDashboard() {
  const navigate = useNavigate();
  const [currentView, setCurrentView] = useState<AdminView>('dashboard');
  const { data: tasks, refetch: refetchTasks } = useTasks();
  const { data: users, refetch: refetchUsers } = useUsers();

  // Task creation state
  const [taskType, setTaskType] = useState<TaskType>('QA');
  const [inputData, setInputData] = useState(taskInputPlaceholders.QA);
  const [yamlBatch, setYamlBatch] = useState('tasks:\n  - task_type: QA\n    input_data:\n      question: "..."\n      context: "..."');
  const createTask = useCreateTask();
  const batchCreate = useBatchCreateTasksFromYaml();
  const updateTaskStatus = useUpdateTaskStatus();

  useEffect(() => {
    setInputData(taskInputPlaceholders[taskType] || '{}');
  }, [taskType]);

  // User creation/credential state
  const [username, setUsername] = useState('');
  const [credUserId, setCredUserId] = useState<number | ''>(1);
  const [credType, setCredType] = useState('ACADEMIC_DEGREE');
  const [credValue, setCredValue] = useState('PhD');
  const [credWeight, setCredWeight] = useState(0.4);
  const createUser = useCreateUser();
  const addCredential = useAddCredential();

  // Config management
  const { data: modelConfig } = useModelConfig();
  const { data: taskConfig } = useTaskConfig();
  const updateModelConfig = useUpdateModelConfig();
  const updateTaskConfig = useUpdateTaskConfig();
  const [modelYaml, setModelYaml] = useState<string>('');
  const [taskYaml, setTaskYaml] = useState<string>('');

  useEffect(() => {
    if (modelConfig) setModelYaml(JSON.stringify(modelConfig, null, 2));
  }, [modelConfig]);

  useEffect(() => {
    if (taskConfig) setTaskYaml(JSON.stringify(taskConfig, null, 2));
  }, [taskConfig]);

  // API Key
  const setApiKey = useSetApiKey();
  const [apiKey, setApiKeyInput] = useState<string>('');

  // Export state
  const [exportTaskType, setExportTaskType] = useState<TaskType>('QA');
  const [exportFormat, setExportFormat] = useState('sft');
  const exportDataset = useExportDataset();

  // Fetch system metrics for statistics overview
  const { data: systemMetrics, isLoading: loadingMetrics } = useQuery({
    queryKey: ['system-metrics'],
    queryFn: () => apiClient.analytics.getSystemMetrics(),
    refetchInterval: 30000, // Refresh every 30 seconds
    retry: 2
  });

  const handleAggregate = (taskId: number) => {
    toast.info(`Starting aggregation for task ${taskId}...`);
    updateTaskStatus.mutate({ id: taskId, status: 'AGGREGATED' });
  };

  const handleExport = () => {
    toast.info(`Exporting ${exportTaskType} tasks in ${exportFormat} format...`);
    exportDataset.mutate({ task_type: exportTaskType, export_format: exportFormat });
  };

  // Handle view switching
  if (currentView === 'tasks') {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <Button
            variant="ghost"
            onClick={() => setCurrentView('dashboard')}
            className="text-slate-400 hover:text-white"
          >
            ← Back to Dashboard
          </Button>
        </div>
        <TaskManager />
      </div>
    );
  }

  if (currentView === 'upload') {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <Button
            variant="ghost"
            onClick={() => setCurrentView('dashboard')}
            className="text-slate-400 hover:text-white"
          >
            ← Back to Dashboard
          </Button>
        </div>
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">Upload Dataset</h1>
          <p className="text-slate-400 mb-6">Upload CSV files to create tasks automatically</p>
          <CsvUpload
            onUploadComplete={(tasks) => {
              toast.success(`Successfully created ${tasks.length} tasks`);
              setCurrentView('tasks');
            }}
          />
        </div>
      </div>
    );
  }

  if (currentView === 'ai-config') {
    return (
      <div className="space-y-6">
        <div className="flex items-center gap-4">
          <Button
            variant="ghost"
            onClick={() => setCurrentView('dashboard')}
            className="text-slate-400 hover:text-white"
          >
            ← Back to Dashboard
          </Button>
        </div>
        
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">AI Configuration</h1>
          <p className="text-slate-400 mb-6">Configure OpenRouter integration for realistic AI responses</p>
          <AIConfiguration />
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-white mb-2">Admin Dashboard</h1>
        <p className="text-slate-400">Gestisci tasks, utenti, chiavi e configurazioni del framework</p>
      </div>

      {/* System Statistics Overview */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="border-blue-600/20">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-slate-400 mb-1">Total Tasks</p>
                <p className="text-3xl font-bold text-white">
                  {loadingMetrics ? '...' : (systemMetrics?.totalTasks || tasks?.length || 0)}
                </p>
              </div>
              <div className="p-3 bg-blue-500/10 rounded-full">
                <BarChart className="h-6 w-6 text-blue-400" />
              </div>
            </div>
            <div className="mt-3 flex gap-2">
              <Badge variant="outline" className="text-xs text-green-400 border-green-400">
                {loadingMetrics ? '...' : (systemMetrics?.completionRate ? `${(systemMetrics.completionRate * 100).toFixed(0)}%` : '0%')} completion
              </Badge>
            </div>
          </CardContent>
        </Card>

        <Card className="border-purple-600/20">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-slate-400 mb-1">Total Users</p>
                <p className="text-3xl font-bold text-white">
                  {loadingMetrics ? '...' : (systemMetrics?.totalUsers || users?.length || 0)}
                </p>
              </div>
              <div className="p-3 bg-purple-500/10 rounded-full">
                <Users className="h-6 w-6 text-purple-400" />
              </div>
            </div>
            <div className="mt-3 flex gap-2">
              <Badge variant="outline" className="text-xs text-blue-400 border-blue-400">
                {loadingMetrics ? '...' : (systemMetrics?.activeEvaluations || 0)} active
              </Badge>
            </div>
          </CardContent>
        </Card>

        <Card className="border-green-600/20">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-slate-400 mb-1">Avg Consensus</p>
                <p className="text-3xl font-bold text-white">
                  {loadingMetrics ? '...' : (systemMetrics?.averageConsensus ? `${(systemMetrics.averageConsensus * 100).toFixed(0)}%` : '0%')}
                </p>
              </div>
              <div className="p-3 bg-green-500/10 rounded-full">
                <CheckCircle className="h-6 w-6 text-green-400" />
              </div>
            </div>
            <div className="mt-3 flex gap-2">
              <Badge variant="outline" className="text-xs text-yellow-400 border-yellow-400">
                {loadingMetrics ? '...' : (systemMetrics?.totalFeedback || 0)} feedbacks
              </Badge>
            </div>
          </CardContent>
        </Card>

        <Card className="border-yellow-600/20">
          <CardContent className="p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-slate-400 mb-1">Evaluations</p>
                <p className="text-3xl font-bold text-white">
                  {loadingMetrics ? '...' : (systemMetrics?.activeEvaluations || 0)}
                </p>
              </div>
              <div className="p-3 bg-yellow-500/10 rounded-full">
                <Clock className="h-6 w-6 text-yellow-400" />
              </div>
            </div>
            <div className="mt-3 flex gap-2">
              <Badge variant="outline" className="text-xs text-purple-400 border-purple-400">
                {loadingMetrics ? '...' : (tasks?.filter((t: LegalTask) => t.status === 'BLIND_EVALUATION').length || 0)} in progress
              </Badge>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Quick Actions */}
      <Card>
        <CardHeader>
          <CardTitle>Quick Actions</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
            <Button
              onClick={() => navigate('/admin/ingestion')}
              className="flex items-center gap-2 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700"
            >
              <Database className="h-4 w-4" />
              KG Ingestion
            </Button>
            <Button
              onClick={() => setCurrentView('upload')}
              className="flex items-center gap-2"
            >
              <Upload className="h-4 w-4" />
              Upload CSV Dataset
            </Button>
            <Button
              variant="outline"
              onClick={() => setCurrentView('tasks')}
              className="flex items-center gap-2"
            >
              <RefreshCw className="h-4 w-4" />
              Manage Tasks
            </Button>
            <Button
              variant="outline"
              onClick={() => setCurrentView('ai-config')}
              className="flex items-center gap-2"
            >
              🤖 AI Configuration
            </Button>
            <Button
              variant="outline"
              onClick={handleExport}
              className="flex items-center gap-2"
              disabled={exportDataset.isPending}
            >
              <Download className="h-4 w-4" />
              Export Data
            </Button>
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
        {/* User Management Column */}
        <div className="space-y-6 xl:col-span-1">
          <Card>
            <CardHeader>
              <CardTitle>User Management</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <label className="block text-sm text-slate-300">New Username</label>
                <input className="w-full p-2 bg-slate-900 border border-slate-700 rounded" value={username} onChange={(e) => setUsername(e.target.value)} />
                <div className="flex justify-end">
                  <Button onClick={() => username && createUser.mutate(username)}>Create User</Button>
                </div>
              </div>

              <div className="space-y-2 border-t border-slate-700 pt-4">
                <label className="block text-sm text-slate-300 font-medium">Add Credential</label>
                <div className="grid grid-cols-2 gap-2 items-end">
                  <div className="col-span-2">
                    <label className="block text-xs text-slate-400">User ID</label>
                    <input type="number" className="w-full p-2 bg-slate-900 border border-slate-700 rounded" value={credUserId} onChange={(e) => setCredUserId(e.target.value === '' ? '' : Number(e.target.value))} />
                  </div>
                  <div className="col-span-2">
                    <label className="block text-xs text-slate-400">Type</label>
                    <select className="w-full p-2 bg-slate-900 border border-slate-700 rounded" value={credType} onChange={(e) => setCredType(e.target.value)}>
                      {['ACADEMIC_DEGREE','PROFESSIONAL_EXPERIENCE','PUBLICATION','INSTITUTIONAL_ROLE'].map(t => <option key={t} value={t}>{t}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="block text-xs text-slate-400">Value</label>
                    <input className="w-full p-2 bg-slate-900 border border-slate-700 rounded" value={credValue} onChange={(e) => setCredValue(e.target.value)} />
                  </div>
                  <div>
                    <label className="block text-xs text-slate-400">Weight</label>
                    <input type="number" min={0} max={1} step={0.05} className="w-full p-2 bg-slate-900 border border-slate-700 rounded" value={credWeight} onChange={(e) => setCredWeight(Number(e.target.value))} />
                  </div>
                  <div className="col-span-2 flex justify-end">
                    <Button onClick={() => {
                      if (credUserId === '') return;
                      addCredential.mutate({ id: credUserId as number, credential: { type: credType, value: credValue, weight: credWeight } });
                    }}>Add Credential</Button>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Data Export</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <label className="block text-sm text-slate-300">Task Type</label>
                <select className="w-full p-2 bg-slate-900 border border-slate-700 rounded" value={exportTaskType} onChange={(e) => setExportTaskType(e.target.value as TaskType)}>
                  {Object.values('QA').map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
              <div className="space-y-2">
                <label className="block text-sm text-slate-300">Format</label>
                <select className="w-full p-2 bg-slate-900 border border-slate-700 rounded" value={exportFormat} onChange={(e) => setExportFormat(e.target.value)}>
                  <option value="sft">SFT (JSONL)</option>
                  <option value="preference">Preference (JSONL)</option>
                </select>
              </div>
              <div className="flex justify-end">
                <Button onClick={handleExport} icon={<Download className="h-4 w-4" />} loading={exportDataset.isPending}>
                  Export Data
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Task Management Column */}
        <div className="space-y-6 xl:col-span-2">
          <Card>
            <CardHeader>
              <CardTitle>Task Creation</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div>
                  <label className="block text-sm text-slate-300 mb-2 font-medium">Create Single Task</label>
                  <div className="space-y-2">
                    <label className="block text-xs text-slate-400">Task Type</label>
                    <select className="w-full p-2 bg-slate-900 border border-slate-700 rounded" value={taskType} onChange={(e) => setTaskType(e.target.value as TaskType)}>
                      {Object.keys(taskInputPlaceholders).map(t => (
                        <option key={t} value={t}>{t}</option>
                      ))}
                    </select>
                  </div>
                  <div className="space-y-2 mt-2">
                    <label className="block text-xs text-slate-400">Input Data (JSON)</label>
                    <textarea className="w-full p-2 bg-slate-900 border border-slate-700 rounded font-mono text-xs" rows={6} value={inputData} onChange={(e) => setInputData(e.target.value)} />
                  </div>
                  <div className="flex justify-end mt-2">
                    <Button onClick={() => {
                      try {
                        const parsed = JSON.parse(inputData);
                        createTask.mutate({ task_type: taskType, input_data: parsed } as Partial<LegalTask>);
                      } catch {
                        toast.error('Invalid JSON for input_data');
                      }
                    }}>Create Task</Button>
                  </div>
                </div>
                <div>
                  <label className="block text-sm text-slate-300 mb-2 font-medium">Create Batch from YAML</label>
                  <div className="space-y-2">
                    <label className="block text-xs text-slate-400">YAML Content</label>
                    <textarea className="w-full p-2 bg-slate-900 border border-slate-700 rounded font-mono text-xs" rows={9} value={yamlBatch} onChange={(e) => setYamlBatch(e.target.value)} />
                  </div>
                  <div className="flex justify-end mt-2">
                    <Button onClick={() => batchCreate.mutate(yamlBatch)}>Create Batch</Button>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Full-width Tables */}
      <div className="space-y-6">
        <Card>
          <CardHeader className="flex flex-row justify-between items-center">
            <CardTitle>User List</CardTitle>
            <Button variant="ghost" size="sm" onClick={() => refetchUsers()}><RefreshCw className="h-4 w-4" /></Button>
          </CardHeader>
          <CardContent>
            <div className="max-h-96 overflow-auto text-xs bg-slate-900 border border-slate-800 rounded">
              <table className="w-full text-left">
                <thead className="sticky top-0 bg-slate-900">
                  <tr className="text-slate-400">
                    <th className="p-2">ID</th>
                    <th className="p-2">Username</th>
                    <th className="p-2">Authority</th>
                    <th className="p-2">Baseline</th>
                    <th className="p-2">Track Record</th>
                  </tr>
                </thead>
                <tbody>
                  {(users || []).map((u: User) => (
                    <tr key={u.id} className="border-t border-slate-800 hover:bg-slate-800/50">
                      <td className="p-2">{u.id}</td>
                      <td className="p-2 font-medium text-slate-200">{u.username}</td>
                      <td className="p-2 font-mono text-violet-400">{u.authority_score?.toFixed(3)}</td>
                      <td className="p-2 font-mono">{u.baseline_credential_score?.toFixed(3)}</td>
                      <td className="p-2 font-mono">{u.track_record_score?.toFixed(3)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row justify-between items-center">
            <CardTitle>Task List</CardTitle>
            <Button variant="ghost" size="sm" onClick={() => refetchTasks()}><RefreshCw className="h-4 w-4" /></Button>
          </CardHeader>
          <CardContent>
            <div className="max-h-96 overflow-auto text-xs bg-slate-900 border border-slate-800 rounded">
              <table className="w-full text-left">
                <thead className="sticky top-0 bg-slate-900">
                  <tr className="text-slate-400">
                    <th className="p-2">ID</th>
                    <th className="p-2">Type</th>
                    <th className="p-2">Status</th>
                    <th className="p-2">Input Data</th>
                    <th className="p-2 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody>
                  {(tasks || []).map((t: LegalTask) => (
                    <tr key={t.id} className="border-t border-slate-800 hover:bg-slate-800/50">
                      <td className="p-2">{t.id}</td>
                      <td className="p-2 font-medium text-slate-300">{t.task_type}</td>
                      <td className="p-2"><span className={`px-2 py-1 rounded-full text-xs ${t.status === 'BLIND_EVALUATION' ? 'bg-green-500/20 text-green-400' : 'bg-slate-700 text-slate-300'}`}>{t.status}</span></td>
                      <td className="p-2 font-mono text-slate-400 max-w-md truncate">{JSON.stringify(t.input_data)}</td>
                      <td className="p-2 text-right">
                        {t.status === 'BLIND_EVALUATION' && (
                          <Button size="sm" variant="secondary" onClick={() => handleAggregate(t.id)} loading={updateTaskStatus.isPending}>
                            Aggregate
                          </Button>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

