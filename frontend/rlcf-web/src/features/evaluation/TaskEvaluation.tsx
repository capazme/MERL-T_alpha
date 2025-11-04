import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowLeft } from 'lucide-react';
import { Card, CardContent, CardHeader, CardTitle } from '@components/ui/Card';
import { Button } from '@components/ui/Button';
import { useTasks, useSubmitFeedback, useDevilsAdvocateAssignment } from '@hooks/useApi';
import { apiClient } from '../../lib/api';
import { useUIStore } from '../../app/store/ui';
import type { Response } from '../../types/index';
import { EvaluationWizard } from './components/EvaluationWizard';
import { toast } from 'sonner';

export function TaskEvaluation() {
  const navigate = useNavigate();
  const { data: tasks, isLoading: tasksLoading, error: tasksError } = useTasks({ status: 'BLIND_EVALUATION' } as any);
  const { selectedTask: storeSelectedTask, setSelectedTask } = useUIStore();

  // Debug logging
  console.log('TaskEvaluation Debug:', {
    tasksLoading,
    tasksError,
    tasksCount: tasks?.length,
    tasks: tasks?.slice(0, 2), // First 2 tasks for inspection
  });
  
  // State for evaluation mode and responses
  const [mode, setMode] = useState<'blind' | 'preference'>('blind');
  const [loadingResponse, setLoadingResponse] = useState(false);
  const [responseA, setResponseA] = useState<Response | null>(null);
  const [responseB, setResponseB] = useState<Response | null>(null);

  const selectedTask = storeSelectedTask || (tasks && tasks.length > 0 ? tasks[0] : null);

  useEffect(() => {
    if (!storeSelectedTask && tasks && tasks.length > 0) {
      setSelectedTask(tasks[0]);
    }
  }, [tasks, storeSelectedTask, setSelectedTask]);

  useEffect(() => {
    if (!selectedTask) {
      setResponseA(null);
      setResponseB(null);
      return;
    }

    const loadEvaluationData = async () => {
      setLoadingResponse(true);
      setMode('blind');
      setResponseB(null);
      
      try {
        // Get the actual response from the database for this task
        const response = await apiClient.tasks.getResponses(selectedTask.id);
        if (response && response.length > 0) {
          // Use the first response for this task
          setResponseA(response[0]);
        } else {
          // Fallback to ground truth if available, or placeholder
          const hasGroundTruth = selectedTask.ground_truth_data && selectedTask.ground_truth_data?.answer_text;
          if (hasGroundTruth) {
            setResponseA({ 
              id: -1, 
              task_id: selectedTask.id, 
              model_version: 'ground_truth', 
              output_data: { response_text: selectedTask.ground_truth_data?.answer_text || 'Ground truth not available' }, 
              generated_at: selectedTask.created_at 
            });
          } else {
            setResponseA({ 
              id: -99, 
              task_id: selectedTask.id, 
              model_version: 'placeholder', 
              output_data: { response_text: 'No response available for this task.' }, 
              generated_at: new Date().toISOString() 
            });
          }
        }
      } catch (error) {
        console.error("Failed to load response for task:", error);
        setResponseA({ 
          id: -99, 
          task_id: selectedTask.id, 
          model_version: 'error', 
          output_data: { response_text: 'Error loading response for this task.' }, 
          generated_at: new Date().toISOString() 
        });
      }
      
      setLoadingResponse(false);
    };

    loadEvaluationData();
  }, [selectedTask]);

  const isReady = useMemo(() => selectedTask && !loadingResponse && (responseA || responseB), [selectedTask, loadingResponse, responseA, responseB]);

  const { data: daAssignment } = useDevilsAdvocateAssignment(selectedTask?.id || 0);
  const isDevilsAdvocate = !!daAssignment?.is_assigned;

  const submitFeedback = useSubmitFeedback();

  const handleNextTask = () => {
    if (!tasks || tasks.length === 0) return;
    const idx = selectedTask ? tasks.findIndex((t) => t.id === selectedTask.id) : -1;
    const next = tasks[(idx + 1) % tasks.length];
    setSelectedTask(next);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-white mb-2">Task Evaluation</h1>
          <p className="text-slate-400">Evaluate AI responses for legal tasks</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => navigate('/dashboard')}>
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Dashboard
          </Button>
          <Button variant="secondary" onClick={handleNextTask} disabled={!tasks || tasks.length <= 1}>
            Next Task
          </Button>
        </div>
      </div>

      {tasksLoading ? (
        <Card><CardHeader><CardTitle>Loading tasks...</CardTitle></CardHeader><CardContent><div className="text-slate-400 flex items-center gap-2"><div className="animate-spin h-4 w-4 border-2 border-violet-500 border-t-transparent rounded-full"></div>Loading available tasks</div></CardContent></Card>
      ) : tasksError ? (
        <Card><CardHeader><CardTitle>Error loading tasks</CardTitle></CardHeader><CardContent><p className="text-red-400">Failed to load tasks: {(tasksError as Error).message}</p></CardContent></Card>
      ) : !tasks || tasks.length === 0 ? (
        <Card><CardHeader><CardTitle>No tasks available for evaluation</CardTitle></CardHeader><CardContent><p className="text-slate-400">There are currently no tasks in BLIND_EVALUATION status.</p></CardContent></Card>
      ) : loadingResponse ? (
        <Card><CardHeader><CardTitle>Loading Task Response...</CardTitle></CardHeader><CardContent><div className="text-slate-400 flex items-center gap-2"><div className="animate-spin h-4 w-4 border-2 border-violet-500 border-t-transparent rounded-full"></div>Loading AI response for evaluation</div></CardContent></Card>
      ) : isReady && selectedTask ? (
        <EvaluationWizard
          key={selectedTask.id} // Add key to force re-mount on task change
          task={selectedTask}
          response={responseA!}
          mode={mode}
          responseB={responseB}
          isDevilsAdvocate={isDevilsAdvocate}
          onComplete={(feedback) => {
            const responseId = mode === 'preference' ? (feedback.feedback_data.preference === 'A' ? responseA?.id : responseB?.id) : responseA?.id;
            submitFeedback.mutate(
              { responseId: responseId ?? -1, feedbackData: feedback },
              {
                onSuccess: () => {
                  toast.success('Feedback submitted successfully!');
                  handleNextTask();
                },
                onError: (error) => {
                  toast.error('Failed to submit feedback. Please try again.');
                  console.error('Submission error:', error);
                }
              }
            );
          }}
        />
      ) : null}
    </div>
  );
}
