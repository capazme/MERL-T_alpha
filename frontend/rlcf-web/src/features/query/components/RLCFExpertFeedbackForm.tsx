/**
 * RLCF Expert Feedback Form Component
 *
 * Multi-step form for legal experts to provide RLCF feedback:
 * - Step 1: Concept Mapping corrections
 * - Step 2: Routing improvements
 * - Step 3: Answer Quality vote
 */

import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Card, CardHeader, CardTitle, CardContent } from '@components/ui/Card';
import { Button } from '@components/ui/Button';
import { Textarea } from '@components/ui/Textarea';
import { Badge } from '@components/ui/Badge';
import { useSubmitRlcfFeedback } from '@hooks/useOrchestration';
import { useAuthStore } from '@/app/store/auth';
import {
  Brain,
  GitBranch,
  ThumbsUp,
  ThumbsDown,
  HelpCircle,
  CheckCircle,
  Loader,
  ArrowRight,
  ArrowLeft,
} from 'lucide-react';
import type { RLCFFeedbackRequest } from '@/types/orchestration';

// Validation schema
const rlcfFeedbackSchema = z.object({
  // Concept Mapping
  concept_mapping_issues: z.string().max(1000).optional(),
  concept_mapping_suggestions: z.string().max(1000).optional(),

  // Routing
  routing_was_appropriate: z.boolean().optional(),
  routing_suggestions: z.string().max(1000).optional(),

  // Answer Quality
  answer_vote: z.enum(['approve', 'reject', 'uncertain']),
  answer_reasoning: z.string().min(20, 'Fornisci una motivazione di almeno 20 caratteri').max(2000),
  answer_improvements: z.string().max(2000).optional(),
});

type RLCFFeedbackFormData = z.infer<typeof rlcfFeedbackSchema>;

interface RLCFExpertFeedbackFormProps {
  traceId: string;
  onSuccess?: () => void;
}

export function RLCFExpertFeedbackForm({ traceId, onSuccess }: RLCFExpertFeedbackFormProps) {
  const { user } = useAuthStore();
  const [currentStep, setCurrentStep] = useState(1);
  const [submitted, setSubmitted] = useState(false);

  const { mutate: submitFeedback, isPending } = useSubmitRlcfFeedback();

  const {
    register,
    handleSubmit,
    formState: { errors },
    watch,
    reset,
  } = useForm<RLCFFeedbackFormData>({
    resolver: zodResolver(rlcfFeedbackSchema),
    mode: 'onChange',
    defaultValues: {
      concept_mapping_issues: '',
      concept_mapping_suggestions: '',
      routing_was_appropriate: undefined,
      routing_suggestions: '',
      answer_vote: undefined,
      answer_reasoning: '',
      answer_improvements: '',
    },
  });

  const answerVote = watch('answer_vote');
  const routingAppropriate = watch('routing_was_appropriate');

  const onSubmit = (data: RLCFFeedbackFormData) => {
    const feedbackRequest: RLCFFeedbackRequest = {
      trace_id: traceId,
      expert_id: user?.username || 'anonymous',
      authority_score: user?.authority_score || undefined,
      corrections: {
        concept_mapping: data.concept_mapping_issues || data.concept_mapping_suggestions
          ? {
              incorrect_entities: data.concept_mapping_issues ? [data.concept_mapping_issues] : undefined,
              missing_entities: data.concept_mapping_suggestions ? [data.concept_mapping_suggestions] : undefined,
            }
          : null,
        routing: data.routing_was_appropriate !== undefined || data.routing_suggestions
          ? {
              inappropriate_agents: data.routing_was_appropriate === false && data.routing_suggestions
                ? [data.routing_suggestions]
                : undefined,
            }
          : null,
        answer_quality: {
          vote: data.answer_vote,
          reasoning: data.answer_reasoning,
          suggested_improvements: data.answer_improvements || null,
        },
      },
    };

    submitFeedback(feedbackRequest, {
      onSuccess: () => {
        setSubmitted(true);
        setTimeout(() => {
          reset();
          setCurrentStep(1);
          setSubmitted(false);
          onSuccess?.();
        }, 3000);
      },
      onError: (error: any) => {
        console.error('Failed to submit RLCF feedback:', error);
      },
    });
  };

  const canProceedToNextStep = (): boolean => {
    if (currentStep === 1) return true; // Concept mapping is optional
    if (currentStep === 2) return true; // Routing is optional
    if (currentStep === 3) {
      const reasoning = watch('answer_reasoning');
      return answerVote !== undefined && reasoning && reasoning.length >= 20;
    }
    return false;
  };

  // Success state
  if (submitted) {
    return (
      <Card className="border-green-500/30">
        <CardContent className="py-12 text-center">
          <CheckCircle className="w-16 h-16 text-green-400 mx-auto mb-4" />
          <h3 className="text-xl font-semibold text-white mb-2">
            Feedback RLCF Inviato!
          </h3>
          <p className="text-gray-400 max-w-md mx-auto">
            Grazie per il tuo contributo come esperto. Il tuo feedback rafforzerà l'autorità
            del sistema e migliorerà le future risposte attraverso il principio RLCF.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-start justify-between">
          <div className="flex-1">
            <CardTitle className="flex items-center gap-2">
              <Brain className="w-5 h-5 text-purple-400" />
              Feedback Esperto RLCF
            </CardTitle>
            <p className="text-sm text-gray-400 mt-2">
              Contribuisci come esperto legale per migliorare il sistema attraverso RLCF
              (Reinforcement Learning from Community Feedback)
            </p>
          </div>
          <Badge variant="outline" className="text-purple-300 border-purple-500/40">
            Esperto
          </Badge>
        </div>
      </CardHeader>

      <CardContent>
        {/* Step Indicator */}
        <div className="flex items-center gap-2 mb-8">
          {[1, 2, 3].map((step) => (
            <div key={step} className="flex items-center flex-1">
              <div
                className={`flex items-center justify-center w-8 h-8 rounded-full font-semibold transition-colors ${
                  currentStep === step
                    ? 'bg-purple-600 text-white'
                    : currentStep > step
                      ? 'bg-green-600 text-white'
                      : 'bg-gray-700 text-gray-400'
                }`}
              >
                {currentStep > step ? <CheckCircle className="w-5 h-5" /> : step}
              </div>
              {step < 3 && (
                <div
                  className={`flex-1 h-1 mx-2 transition-colors ${
                    currentStep > step ? 'bg-green-600' : 'bg-gray-700'
                  }`}
                />
              )}
            </div>
          ))}
        </div>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
          {/* Step 1: Concept Mapping */}
          {currentStep === 1 && (
            <div className="space-y-6">
              <div className="flex items-start gap-3 p-4 bg-purple-500/10 border border-purple-500/30 rounded-lg">
                <Brain className="w-5 h-5 text-purple-400 mt-0.5 flex-shrink-0" />
                <div className="flex-1">
                  <h3 className="text-base font-semibold text-white mb-1">
                    Step 1: Concept Mapping
                  </h3>
                  <p className="text-sm text-purple-200/80">
                    Verifica l'identificazione dei concetti legali nella query (NER, entity
                    linking, normativa rilevante). Segnala eventuali errori o suggerisci
                    miglioramenti.
                  </p>
                </div>
              </div>

              <Textarea
                {...register('concept_mapping_issues')}
                label="Problemi Identificati (opzionale)"
                placeholder="Es: L'entità 'contratto di appalto' non è stata correttamente identificata come contratto tipico, la norma Art. 1655 CC non è stata collegata..."
                maxLength={1000}
                showCharCount
                rows={4}
                disabled={isPending}
                helperText="Descrivi eventuali errori nell'identificazione o categorizzazione dei concetti legali"
              />

              <Textarea
                {...register('concept_mapping_suggestions')}
                label="Suggerimenti di Mappatura (opzionale)"
                placeholder="Es: Aggiungere mappatura a 'contratto di appalto' → Art. 1655-1677 CC, collegare a giurisprudenza Cass. n. 12345/2023..."
                maxLength={1000}
                showCharCount
                rows={4}
                disabled={isPending}
                helperText="Suggerisci mappature alternative o aggiuntive per migliorare la comprensione"
              />
            </div>
          )}

          {/* Step 2: Routing */}
          {currentStep === 2 && (
            <div className="space-y-6">
              <div className="flex items-start gap-3 p-4 bg-blue-500/10 border border-blue-500/30 rounded-lg">
                <GitBranch className="w-5 h-5 text-blue-400 mt-0.5 flex-shrink-0" />
                <div className="flex-1">
                  <h3 className="text-base font-semibold text-white mb-1">
                    Step 2: Routing Evaluation
                  </h3>
                  <p className="text-sm text-blue-200/80">
                    Valuta se il Router LLM ha selezionato gli agenti di retrieval corretti
                    (Knowledge Graph, API, VectorDB) e se gli esperti consultati erano appropriati.
                  </p>
                </div>
              </div>

              <div className="space-y-3">
                <label className="block text-sm font-medium text-gray-300">
                  Il routing era appropriato?
                </label>
                <div className="flex gap-3">
                  <label className="flex-1 flex items-center gap-3 p-4 bg-gray-800 rounded-lg hover:bg-gray-700 transition-colors cursor-pointer group border-2 border-transparent has-[:checked]:border-green-500">
                    <input
                      type="radio"
                      {...register('routing_was_appropriate')}
                      value={true as any}
                      disabled={isPending}
                      className="w-4 h-4 text-green-600 cursor-pointer"
                    />
                    <div className="flex-1">
                      <div className="text-sm font-medium text-white">Sì</div>
                      <div className="text-xs text-gray-500">Gli agenti erano appropriati</div>
                    </div>
                  </label>

                  <label className="flex-1 flex items-center gap-3 p-4 bg-gray-800 rounded-lg hover:bg-gray-700 transition-colors cursor-pointer group border-2 border-transparent has-[:checked]:border-red-500">
                    <input
                      type="radio"
                      {...register('routing_was_appropriate')}
                      value={false as any}
                      disabled={isPending}
                      className="w-4 h-4 text-red-600 cursor-pointer"
                    />
                    <div className="flex-1">
                      <div className="text-sm font-medium text-white">No</div>
                      <div className="text-xs text-gray-500">
                        Il routing andrebbe migliorato
                      </div>
                    </div>
                  </label>
                </div>
              </div>

              {routingAppropriate === false && (
                <Textarea
                  {...register('routing_suggestions')}
                  label="Suggerimenti di Routing"
                  placeholder="Es: Per query su contratti dovrebbe consultare anche l'Agente API Normattiva per ottenere testo completo norme, non solo Knowledge Graph..."
                  maxLength={1000}
                  showCharCount
                  rows={4}
                  disabled={isPending}
                  helperText="Descrivi quali agenti avrebbero dovuto essere consultati o evitati"
                />
              )}

              {routingAppropriate === undefined && (
                <p className="text-xs text-gray-500 italic">
                  Lascia vuoto se non hai feedback specifico sul routing
                </p>
              )}
            </div>
          )}

          {/* Step 3: Answer Quality */}
          {currentStep === 3 && (
            <div className="space-y-6">
              <div className="flex items-start gap-3 p-4 bg-green-500/10 border border-green-500/30 rounded-lg">
                <ThumbsUp className="w-5 h-5 text-green-400 mt-0.5 flex-shrink-0" />
                <div className="flex-1">
                  <h3 className="text-base font-semibold text-white mb-1">
                    Step 3: Answer Quality Vote
                  </h3>
                  <p className="text-sm text-green-200/80">
                    Esprimi il tuo voto sulla qualità complessiva della risposta come esperto
                    legale. Il tuo voto influenzerà il punteggio di autorità RLCF.
                  </p>
                </div>
              </div>

              <div className="space-y-3">
                <label className="block text-sm font-medium text-gray-300">
                  Voto sulla Qualità <span className="text-red-400">*</span>
                </label>
                <div className="grid grid-cols-3 gap-3">
                  <label className="flex flex-col items-center gap-3 p-4 bg-gray-800 rounded-lg hover:bg-gray-700 transition-colors cursor-pointer border-2 border-transparent has-[:checked]:border-green-500">
                    <input
                      type="radio"
                      {...register('answer_vote')}
                      value="approve"
                      disabled={isPending}
                      className="sr-only"
                    />
                    <ThumbsUp
                      className={`w-8 h-8 ${answerVote === 'approve' ? 'text-green-400' : 'text-gray-600'}`}
                    />
                    <div className="text-center">
                      <div className="text-sm font-medium text-white">Approvo</div>
                      <div className="text-xs text-gray-500">Risposta corretta</div>
                    </div>
                  </label>

                  <label className="flex flex-col items-center gap-3 p-4 bg-gray-800 rounded-lg hover:bg-gray-700 transition-colors cursor-pointer border-2 border-transparent has-[:checked]:border-yellow-500">
                    <input
                      type="radio"
                      {...register('answer_vote')}
                      value="uncertain"
                      disabled={isPending}
                      className="sr-only"
                    />
                    <HelpCircle
                      className={`w-8 h-8 ${answerVote === 'uncertain' ? 'text-yellow-400' : 'text-gray-600'}`}
                    />
                    <div className="text-center">
                      <div className="text-sm font-medium text-white">Incerto</div>
                      <div className="text-xs text-gray-500">Necessita verifica</div>
                    </div>
                  </label>

                  <label className="flex flex-col items-center gap-3 p-4 bg-gray-800 rounded-lg hover:bg-gray-700 transition-colors cursor-pointer border-2 border-transparent has-[:checked]:border-red-500">
                    <input
                      type="radio"
                      {...register('answer_vote')}
                      value="reject"
                      disabled={isPending}
                      className="sr-only"
                    />
                    <ThumbsDown
                      className={`w-8 h-8 ${answerVote === 'reject' ? 'text-red-400' : 'text-gray-600'}`}
                    />
                    <div className="text-center">
                      <div className="text-sm font-medium text-white">Respingo</div>
                      <div className="text-xs text-gray-500">Risposta errata</div>
                    </div>
                  </label>
                </div>
                {errors.answer_vote && (
                  <p className="text-xs text-red-400">Seleziona un voto</p>
                )}
              </div>

              <Textarea
                {...register('answer_reasoning')}
                label={
                  <span>
                    Motivazione del Voto <span className="text-red-400">*</span>
                  </span>
                }
                placeholder="Spiega perché hai espresso questo voto: quali aspetti della risposta sono corretti o errati? Quali norme/precedenti supportano o contraddicono la risposta?"
                maxLength={2000}
                showCharCount
                rows={5}
                disabled={isPending}
                error={errors.answer_reasoning?.message}
                helperText="Minimo 20 caratteri. Fornisci una motivazione dettagliata e argomentata"
              />

              <Textarea
                {...register('answer_improvements')}
                label="Suggerimenti di Miglioramento (opzionale)"
                placeholder="Come miglioreresti questa risposta? Quali norme/precedenti andrebbero aggiunti? Come riformuleresti certe parti?"
                maxLength={2000}
                showCharCount
                rows={4}
                disabled={isPending}
                helperText="Suggerimenti concreti per migliorare la qualità della risposta"
              />
            </div>
          )}

          {/* Navigation Buttons */}
          <div className="flex items-center justify-between pt-6 border-t border-gray-700">
            <div>
              {currentStep > 1 && (
                <Button
                  type="button"
                  variant="ghost"
                  onClick={() => setCurrentStep(currentStep - 1)}
                  disabled={isPending}
                >
                  <ArrowLeft className="w-4 h-4 mr-2" />
                  Indietro
                </Button>
              )}
            </div>

            <div className="flex items-center gap-3">
              {currentStep < 3 ? (
                <Button
                  type="button"
                  onClick={() => setCurrentStep(currentStep + 1)}
                  disabled={!canProceedToNextStep() || isPending}
                >
                  Avanti
                  <ArrowRight className="w-4 h-4 ml-2" />
                </Button>
              ) : (
                <Button
                  type="submit"
                  disabled={!canProceedToNextStep() || isPending}
                  loading={isPending}
                  className="min-w-[160px]"
                >
                  {isPending ? (
                    <>
                      <Loader className="w-4 h-4 mr-2 animate-spin" />
                      Invio...
                    </>
                  ) : (
                    <>
                      <Brain className="w-4 h-4 mr-2" />
                      Invia Feedback
                    </>
                  )}
                </Button>
              )}
            </div>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
