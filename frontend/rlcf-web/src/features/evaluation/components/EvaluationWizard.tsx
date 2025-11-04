import { useEffect, useMemo, useState } from 'react';
import { z } from 'zod';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import type { LegalTask, Response, FeedbackData } from '../../../types/index';
import { Card, CardContent, CardHeader, CardTitle } from '../../../components/ui/Card';
import { Button } from '../../../components/ui/Button';
import { Badge } from '../../../components/ui/Badge';
import { TaskFormFields, getSchemaForTaskType } from '../forms/TaskFormFactory';
import { PreferenceForm, preferenceSchema } from '../forms/PreferenceForm';
import { useAuthStore } from '../../../app/store/auth';
import { useEvaluationStore } from '../../../app/store/evaluation';
import { TaskDisplay } from './TaskDisplay';
import { QualityScoring } from './QualityScoring';
import { EvaluationProgress } from './EvaluationProgress';
import { apiClient } from '../../../lib/api';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';

interface EvaluationWizardProps {
  task: LegalTask;
  response: Response;
  mode?: 'blind' | 'preference';
  responseB?: Response | null;
  isDevilsAdvocate?: boolean;
  onComplete: (feedback: FeedbackData) => void;
  onCancel?: () => void;
}

export function EvaluationWizard({ 
  task, 
  response, 
  mode = 'blind', 
  responseB, 
  isDevilsAdvocate = false, 
  onComplete,
  onCancel 
}: EvaluationWizardProps) {
  const { user } = useAuthStore();
  const { currentEvaluation, startEvaluation, nextStep, previousStep, setFormData, goToStep } = useEvaluationStore();

  // Early return if required props are missing
  if (!task || !response) {
    return (
      <div className="max-w-4xl mx-auto">
        <Card className="border-red-700 bg-red-950/20">
          <CardContent className="text-center py-12">
            <div className="text-4xl mb-4">⚠️</div>
            <h3 className="text-xl font-semibold text-red-400 mb-2">Missing Data</h3>
            <p className="text-red-200">Task and response data are required for evaluation.</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  const [currentStep, setCurrentStep] = useState(1);
  const [startTime] = useState(Date.now());
  const [scores, setScores] = useState({ accuracy: 8, utility: 8, transparency: 8 });
  const [devilsAdvocatePrompts, setDevilsAdvocatePrompts] = useState<string[]>([]);
  
  // Timer per tracciare il tempo speso
  const [timeSpent, setTimeSpent] = useState(0);
  
  useEffect(() => {
    const interval = setInterval(() => {
      setTimeSpent(Date.now() - startTime);
    }, 1000);
    return () => clearInterval(interval);
  }, [startTime]);

  // Fetch devil's advocate prompts if needed
  const { data: advocatePromptsData, error: advocatePromptsError } = useQuery({
    queryKey: ['devils-advocate-prompts', task.task_type],
    queryFn: () => apiClient.devilsAdvocate.getCriticalPrompts(task.task_type),
    enabled: isDevilsAdvocate,
    staleTime: 5 * 60 * 1000, // 5 minutes
    retry: 2,
  });

  useEffect(() => {
    if (advocatePromptsData && isDevilsAdvocate) {
      setDevilsAdvocatePrompts(advocatePromptsData.prompts || []);
    }
  }, [advocatePromptsData, isDevilsAdvocate]);

  // Show error toast if devil's advocate prompts fail to load
  useEffect(() => {
    if (advocatePromptsError && isDevilsAdvocate) {
      toast.error('Failed to load Devil\'s Advocate prompts', {
        description: 'Using default critical evaluation guidelines.'
      });
    }
  }, [advocatePromptsError, isDevilsAdvocate]);

  const schema = useMemo(() => 
    mode === 'preference' ? preferenceSchema : getSchemaForTaskType(task.task_type),
    [mode, task.task_type]
  );

  const {
    register,
    handleSubmit,
    setValue,
    formState: { errors },
    watch,
    reset,
    getValues
  } = useForm<z.infer<typeof schema>>({
    resolver: zodResolver(schema),
    defaultValues: {},
  });

  // Auto-save form data to localStorage
  const formData = watch();
  useEffect(() => {
    if (Object.keys(formData).length > 0 && task?.id && response?.id) {
      localStorage.setItem(`evaluation-draft-${task.id}-${response.id}`, JSON.stringify(formData));
    }
  }, [formData, task?.id, response?.id]);

  // Load draft from localStorage on mount
  useEffect(() => {
    if (!task?.id || !response?.id) return;
    
    const draft = localStorage.getItem(`evaluation-draft-${task.id}-${response.id}`);
    if (draft) {
      try {
        const parsedDraft = JSON.parse(draft);
        Object.keys(parsedDraft).forEach(key => {
          setValue(key as any, parsedDraft[key]);
        });
      } catch (error) {
        console.warn('Failed to load evaluation draft:', error);
      }
    }
  }, [task?.id, response?.id, setValue]);

  const queryClient = useQueryClient();

  // Mutation for feedback submission with optimistic updates
  const submitFeedbackMutation = useMutation({
    mutationFn: async (feedbackPayload: FeedbackData) => {
      return await onComplete(feedbackPayload);
    },
    onMutate: async () => {
      // Show loading toast
      toast.loading('Submitting your evaluation...', { id: 'submit-feedback' });
    },
    onSuccess: () => {
      // Invalidate queries to refresh data
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
      queryClient.invalidateQueries({ queryKey: ['feedback'] });
      queryClient.invalidateQueries({ queryKey: ['user', user?.id] });

      // Clear draft after successful submission
      if (task?.id && response?.id) {
        localStorage.removeItem(`evaluation-draft-${task.id}-${response.id}`);
      }

      // Show success toast
      toast.success('Evaluation submitted successfully! 🎉', {
        id: 'submit-feedback',
        description: `Your authority score will be updated based on peer validation.`
      });

      setCurrentStep(4); // Success step
    },
    onError: (error: Error) => {
      console.error('Failed to submit evaluation:', error);
      toast.error('Failed to submit evaluation', {
        id: 'submit-feedback',
        description: error.message || 'Please try again or contact support if the issue persists.'
      });
    }
  });

  const onSubmit = async (data: z.infer<typeof schema>) => {
    if (!user) {
      toast.error('Authentication required', {
        description: 'Please log in to submit evaluations.'
      });
      return;
    }

    // Validate scores
    if (scores.accuracy < 1 || scores.utility < 1 || scores.transparency < 1) {
      toast.error('Invalid scores', {
        description: 'All quality scores must be at least 1.'
      });
      return;
    }

    const feedbackPayload: FeedbackData = {
      user_id: user.id,
      accuracy_score: scores.accuracy,
      utility_score: scores.utility,
      transparency_score: scores.transparency,
      feedback_data: { ...data },
      metadata: {
        mode,
        time_spent_ms: timeSpent,
        is_devils_advocate: isDevilsAdvocate,
        task_type: task.task_type,
        response_id: response.id,
        ...(mode === 'preference' && {
          response_a_id: response.id,
          response_b_id: responseB?.id
        }),
        timestamp: new Date().toISOString(),
      },
    };

    submitFeedbackMutation.mutate(feedbackPayload);
  };
  
  const formatTime = (ms: number) => {
    const seconds = Math.floor(ms / 1000);
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
  };
  
  const handleNext = async () => {
    // Validate current step before proceeding
    if (currentStep === 2) {
      // Trigger form validation
      const isValid = await handleSubmit(
        () => {
          // If validation passes, move to next step
          toast.success('Form validated successfully');
          setCurrentStep(prev => prev + 1);
        },
        (errors) => {
          // Validation failed - show error feedback
          const errorCount = Object.keys(errors).length;
          toast.error('Form validation failed', {
            description: `Please fix ${errorCount} error${errorCount > 1 ? 's' : ''} before continuing.`
          });

          // Log errors for debugging
          console.warn('Form validation errors:', errors);
        }
      )();
    } else {
      setCurrentStep(prev => prev + 1);
    }
  };

  const handlePrevious = () => {
    setCurrentStep(prev => prev - 1);
  };
  
  const handleCancel = () => {
    if (onCancel) {
      onCancel();
    }
  };

  // Keyboard shortcuts for navigation
  useEffect(() => {
    const handleKeyPress = (e: KeyboardEvent) => {
      // Only handle if not typing in an input/textarea
      if (
        e.target instanceof HTMLInputElement ||
        e.target instanceof HTMLTextAreaElement ||
        submitFeedbackMutation.isPending
      ) {
        return;
      }

      // Alt+Right: Next step
      if (e.altKey && e.key === 'ArrowRight' && currentStep < 4) {
        e.preventDefault();
        handleNext();
      }

      // Alt+Left: Previous step
      if (e.altKey && e.key === 'ArrowLeft' && currentStep > 1) {
        e.preventDefault();
        handlePrevious();
      }

      // Ctrl+S or Cmd+S: Save draft
      if ((e.ctrlKey || e.metaKey) && e.key === 's' && currentStep === 2) {
        e.preventDefault();
        const draftData = getValues();
        if (Object.keys(draftData).length > 0) {
          localStorage.setItem(
            `evaluation-draft-${task.id}-${response.id}`,
            JSON.stringify(draftData)
          );
          toast.success('Draft saved locally', {
            description: 'Your progress has been saved.'
          });
        }
      }
    };

    window.addEventListener('keydown', handleKeyPress);
    return () => window.removeEventListener('keydown', handleKeyPress);
  }, [currentStep, task.id, response.id, submitFeedbackMutation.isPending]);

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      {/* Header with progress and metadata */}
      <Card className="border-purple-700 bg-slate-900/50">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-3">
                <span className="text-2xl">⚖️</span>
                RLCF Evaluation Wizard
                {isDevilsAdvocate && (
                  <Badge variant="destructive" className="ml-2">
                    👹 Devil's Advocate
                  </Badge>
                )}
              </CardTitle>
              <p className="text-slate-400 mt-1">
                Task #{task.id} • {task.task_type} • Time: {formatTime(timeSpent)}
              </p>
            </div>
            <div className="text-right">
              <div className="text-sm text-slate-400">Authority Score</div>
              <div className="text-xl font-bold text-purple-400">{user?.authority_score || 0}</div>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <EvaluationProgress currentStep={currentStep} totalSteps={mode === 'preference' ? 4 : 4} />
        </CardContent>
      </Card>

      {/* Step 1: Task Review */}
      {currentStep === 1 && (
        <div className="space-y-6">
          <Card className="border-slate-700">
            <CardHeader>
              <CardTitle>📋 Step 1: Review Task & Response</CardTitle>
              <p className="text-slate-400">Please carefully review the legal task and AI-generated response before proceeding.</p>
            </CardHeader>
            <CardContent>
              <TaskDisplay 
                task={task} 
                mode={mode} 
                responseA={response} 
                responseB={responseB} 
              />
              
              {isDevilsAdvocate && devilsAdvocatePrompts.length > 0 && (
                <div className="mt-6 p-4 border-2 border-red-700 rounded-lg bg-red-950/20">
                  <h4 className="text-lg font-semibold text-red-400 mb-3">👹 Devil's Advocate Instructions</h4>
                  <div className="space-y-2">
                    {devilsAdvocatePrompts.map((prompt, idx) => (
                      <p key={idx} className="text-red-200 text-sm">• {prompt}</p>
                    ))}
                  </div>
                  <p className="text-red-300 text-sm mt-3 font-medium">
                    ⚠️ Your role is to provide constructive critical analysis to improve overall quality.
                  </p>
                </div>
              )}
            </CardContent>
          </Card>
          
          <div className="flex justify-between">
            <Button variant="outline" onClick={handleCancel}>Cancel</Button>
            <Button onClick={handleNext} size="lg" className="bg-purple-600 hover:bg-purple-700">
              Continue to Evaluation →
            </Button>
          </div>
        </div>
      )}

      {/* Step 2: Blind Evaluation Form */}
      {currentStep === 2 && (
        <Card className="border-slate-700">
          <CardHeader>
            <CardTitle>
              🔍 Step 2: {mode === 'preference' ? 'Preference Evaluation' : 'Blind Evaluation'}
            </CardTitle>
            <p className="text-slate-400">
              Provide detailed feedback according to RLCF framework principles.
            </p>

            {/* Form Completion Progress */}
            {(() => {
              const formValues = getValues();
              const requiredFields = Object.keys(schema.shape);
              const filledFields = requiredFields.filter(field => {
                const value = formValues[field as keyof typeof formValues];
                return value !== undefined && value !== '' && value !== null;
              });
              const completionPercentage = Math.round((filledFields.length / requiredFields.length) * 100);

              return (
                <div className="mt-4 space-y-2">
                  <div className="flex items-center justify-between text-sm">
                    <span className="text-slate-400">Form Completion</span>
                    <span className="font-medium text-purple-400">
                      {filledFields.length}/{requiredFields.length} fields ({completionPercentage}%)
                    </span>
                  </div>
                  <div className="w-full bg-slate-700 rounded-full h-2">
                    <div
                      className="bg-purple-500 h-2 rounded-full transition-all duration-300"
                      style={{ width: `${completionPercentage}%` }}
                    />
                  </div>
                </div>
              );
            })()}
          </CardHeader>
          <CardContent>
            <form className="space-y-6">
              {mode === 'preference' ? (
                <PreferenceForm register={register} errors={errors} />
              ) : (
                <TaskFormFields
                  taskType={task.task_type}
                  register={register}
                  setValue={setValue}
                  errors={errors}
                />
              )}
            </form>
            
            <div className="space-y-4">
              {/* Manual Save Draft Button */}
              <div className="flex items-center justify-between p-3 bg-slate-800/50 rounded-lg">
                <div className="text-sm text-slate-400">
                  <p>💡 Your progress is auto-saved every few seconds</p>
                  <p className="text-xs mt-1">Keyboard shortcuts: Alt+← Previous | Alt+→ Next | Ctrl/Cmd+S Save</p>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => {
                    const draftData = getValues();
                    if (Object.keys(draftData).length > 0) {
                      localStorage.setItem(
                        `evaluation-draft-${task.id}-${response.id}`,
                        JSON.stringify(draftData)
                      );
                      toast.success('Draft saved manually', {
                        description: 'Your progress has been saved.'
                      });
                    }
                  }}
                >
                  💾 Save Draft
                </Button>
              </div>

              <div className="flex justify-between gap-2 pt-4 border-t border-slate-700">
                <Button variant="outline" onClick={handlePrevious}>← Back</Button>
                <Button onClick={handleNext} size="lg" className="bg-purple-600 hover:bg-purple-700">
                  Continue to Quality Scoring →
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Step 3: Quality Scoring */}
      {currentStep === 3 && (
        <Card className="border-slate-700">
          <CardHeader>
            <CardTitle>📊 Step 3: RLCF Quality Scoring</CardTitle>
            <p className="text-slate-400">
              Rate the response according to the three RLCF dimensions.
            </p>
          </CardHeader>
          <CardContent>
            <QualityScoring scores={scores} onScoreChange={setScores} />
            
            <div className="mt-8 p-4 bg-slate-800/50 rounded-lg">
              <h4 className="font-semibold text-slate-200 mb-2">📝 Evaluation Summary</h4>
              <div className="text-sm text-slate-400 space-y-1">
                <p>• Task Type: <span className="text-slate-200">{task.task_type}</span></p>
                <p>• Mode: <span className="text-slate-200">{mode}</span></p>
                <p>• Time Spent: <span className="text-slate-200">{formatTime(timeSpent)}</span></p>
                <p>• Form Fields: <span className="text-slate-200">{Object.keys(getValues()).length} completed</span></p>
                <p>• Quality Scores:
                  <span className="text-slate-200 ml-1">
                    A:{scores.accuracy}, U:{scores.utility}, T:{scores.transparency}
                  </span>
                  <span className={`ml-2 ${(scores.accuracy + scores.utility + scores.transparency) / 3 >= 7 ? 'text-green-400' : 'text-yellow-400'}`}>
                    (Avg: {((scores.accuracy + scores.utility + scores.transparency) / 3).toFixed(1)})
                  </span>
                </p>
                {isDevilsAdvocate && (
                  <p>• Role: <span className="text-red-400">Devil's Advocate Mode ⚠️</span></p>
                )}
              </div>

              {/* Warnings */}
              {timeSpent < 30000 && (
                <div className="mt-3 p-2 bg-yellow-900/20 border border-yellow-700/50 rounded text-sm text-yellow-300">
                  ⚠️ Quick submission detected ({formatTime(timeSpent)}). Consider reviewing your feedback for thoroughness.
                </div>
              )}
              {(scores.accuracy + scores.utility + scores.transparency) / 3 < 5 && (
                <div className="mt-3 p-2 bg-red-900/20 border border-red-700/50 rounded text-sm text-red-300">
                  ⚠️ Low average score detected. Please ensure your evaluation is accurate and fair.
                </div>
              )}
            </div>
            
            <div className="flex justify-between gap-2 pt-4 border-t border-slate-700 mt-6">
              <Button variant="outline" onClick={handlePrevious} disabled={submitFeedbackMutation.isPending}>
                ← Back
              </Button>
              <Button
                onClick={handleSubmit(onSubmit)}
                size="lg"
                disabled={submitFeedbackMutation.isPending}
                className="bg-green-600 hover:bg-green-700"
              >
                {submitFeedbackMutation.isPending ? (
                  <>⏳ Submitting...</>
                ) : (
                  <>✅ Submit Evaluation</>
                )}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Step 4: Success */}
      {currentStep === 4 && (
        <Card className="border-green-700 bg-green-950/20">
          <CardContent className="text-center py-12">
            <div className="text-6xl mb-4">🎉</div>
            <h3 className="text-2xl font-bold text-green-400 mb-2">Evaluation Submitted Successfully!</h3>
            <p className="text-green-200 mb-6">
              Your feedback has been recorded and will contribute to the RLCF aggregation process.
            </p>
            <div className="bg-green-900/30 rounded-lg p-4 mb-6">
              <h4 className="font-semibold text-green-300 mb-2">📈 Impact Summary</h4>
              <div className="text-sm text-green-200 space-y-1">
                <p>• Authority Score: Will be updated based on peer validation</p>
                <p>• Time Investment: {formatTime(timeSpent)} contributed to research</p>
                <p>• Quality Scores: A:{scores.accuracy}, U:{scores.utility}, T:{scores.transparency}</p>
              </div>
            </div>
            <Button 
              onClick={() => window.location.reload()} 
              className="bg-green-600 hover:bg-green-700"
            >
              Continue to Next Task
            </Button>
          </CardContent>
        </Card>
      )}
    </div>
  );
}