/**
 * User Feedback Form Component
 *
 * Allows users to submit feedback on query answers with:
 * - 1-5 star rating
 * - Optional text feedback
 * - Category checkboxes (accuracy, completeness, clarity, usefulness)
 */

import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Card, CardHeader, CardTitle, CardContent } from '@components/ui/Card';
import { Button } from '@components/ui/Button';
import { Textarea } from '@components/ui/Textarea';
import { StarRating } from '@components/ui/StarRating';
import { useSubmitUserFeedback } from '@hooks/useOrchestration';
import { MessageSquarePlus, CheckCircle, Loader } from 'lucide-react';
import type { UserFeedbackRequest } from '@/types/orchestration';

// Validation schema
const userFeedbackSchema = z.object({
  rating: z.number().int().min(1).max(5),
  feedback_text: z.string().max(2000).optional(),
  categories: z
    .object({
      accuracy: z.boolean().optional(),
      completeness: z.boolean().optional(),
      clarity: z.boolean().optional(),
      usefulness: z.boolean().optional(),
    })
    .optional(),
});

type UserFeedbackFormData = z.infer<typeof userFeedbackSchema>;

interface UserFeedbackFormProps {
  traceId: string;
  onSuccess?: () => void;
}

export function UserFeedbackForm({ traceId, onSuccess }: UserFeedbackFormProps) {
  const [rating, setRating] = useState<number>(0);
  const [submitted, setSubmitted] = useState(false);

  const { mutate: submitFeedback, isPending } = useSubmitUserFeedback();

  const {
    register,
    handleSubmit,
    formState: { errors, isValid },
    watch,
    reset,
  } = useForm<UserFeedbackFormData>({
    resolver: zodResolver(userFeedbackSchema),
    mode: 'onChange',
    defaultValues: {
      rating: 0,
      feedback_text: '',
      categories: {
        accuracy: false,
        completeness: false,
        clarity: false,
        usefulness: false,
      },
    },
  });

  const feedbackText = watch('feedback_text');

  const handleRatingChange = (newRating: number) => {
    setRating(newRating);
  };

  const onSubmit = (data: UserFeedbackFormData) => {
    const feedbackRequest: UserFeedbackRequest = {
      trace_id: traceId,
      rating: rating,
      feedback_text: data.feedback_text || null,
      categories: data.categories || null,
    };

    submitFeedback(feedbackRequest, {
      onSuccess: () => {
        setSubmitted(true);
        setTimeout(() => {
          reset();
          setRating(0);
          setSubmitted(false);
          onSuccess?.();
        }, 3000);
      },
      onError: (error: any) => {
        console.error('Failed to submit user feedback:', error);
      },
    });
  };

  // Success state
  if (submitted) {
    return (
      <Card className="border-green-500/30">
        <CardContent className="py-12 text-center">
          <CheckCircle className="w-16 h-16 text-green-400 mx-auto mb-4" />
          <h3 className="text-xl font-semibold text-white mb-2">
            Feedback Inviato!
          </h3>
          <p className="text-gray-400 max-w-md mx-auto">
            Grazie per il tuo feedback. Ci aiuterà a migliorare il sistema MERL-T e la
            qualità delle risposte legali.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <MessageSquarePlus className="w-5 h-5 text-blue-400" />
          Feedback Utente
        </CardTitle>
        <p className="text-sm text-gray-400 mt-2">
          Valuta la qualità della risposta e aiutaci a migliorare il sistema
        </p>
      </CardHeader>

      <CardContent>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
          {/* Star Rating */}
          <div className="space-y-2">
            <label className="block text-sm font-medium text-gray-300">
              Valutazione Complessiva <span className="text-red-400">*</span>
            </label>
            <div className="flex items-center gap-4">
              <StarRating
                value={rating}
                onChange={handleRatingChange}
                maxRating={5}
                disabled={isPending}
              />
              {rating > 0 && (
                <span className="text-sm text-gray-400">
                  {rating} / 5 {rating === 5 ? '🎉' : rating >= 4 ? '👍' : rating >= 3 ? '👌' : ''}
                </span>
              )}
            </div>
            {rating === 0 && (
              <p className="text-xs text-red-400">Seleziona un rating per procedere</p>
            )}
          </div>

          {/* Feedback Categories */}
          <div className="space-y-3">
            <label className="block text-sm font-medium text-gray-300">
              Categorie di Feedback (opzionale)
            </label>
            <p className="text-xs text-gray-500 mb-3">
              Seleziona gli aspetti che vuoi evidenziare
            </p>

            <div className="space-y-2">
              <label className="flex items-center gap-3 p-3 bg-gray-800 rounded-lg hover:bg-gray-700 transition-colors cursor-pointer group">
                <input
                  type="checkbox"
                  {...register('categories.accuracy')}
                  disabled={isPending}
                  className="w-4 h-4 text-blue-600 bg-gray-700 border-gray-600 rounded focus:ring-blue-500 focus:ring-2 cursor-pointer"
                />
                <div className="flex-1">
                  <div className="text-sm font-medium text-white group-hover:text-blue-300 transition-colors">
                    Accuratezza
                  </div>
                  <div className="text-xs text-gray-500">
                    La risposta è corretta dal punto di vista legale
                  </div>
                </div>
              </label>

              <label className="flex items-center gap-3 p-3 bg-gray-800 rounded-lg hover:bg-gray-700 transition-colors cursor-pointer group">
                <input
                  type="checkbox"
                  {...register('categories.completeness')}
                  disabled={isPending}
                  className="w-4 h-4 text-blue-600 bg-gray-700 border-gray-600 rounded focus:ring-blue-500 focus:ring-2 cursor-pointer"
                />
                <div className="flex-1">
                  <div className="text-sm font-medium text-white group-hover:text-blue-300 transition-colors">
                    Completezza
                  </div>
                  <div className="text-xs text-gray-500">
                    La risposta copre tutti gli aspetti rilevanti
                  </div>
                </div>
              </label>

              <label className="flex items-center gap-3 p-3 bg-gray-800 rounded-lg hover:bg-gray-700 transition-colors cursor-pointer group">
                <input
                  type="checkbox"
                  {...register('categories.clarity')}
                  disabled={isPending}
                  className="w-4 h-4 text-blue-600 bg-gray-700 border-gray-600 rounded focus:ring-blue-500 focus:ring-2 cursor-pointer"
                />
                <div className="flex-1">
                  <div className="text-sm font-medium text-white group-hover:text-blue-300 transition-colors">
                    Chiarezza
                  </div>
                  <div className="text-xs text-gray-500">
                    La risposta è facile da comprendere
                  </div>
                </div>
              </label>

              <label className="flex items-center gap-3 p-3 bg-gray-800 rounded-lg hover:bg-gray-700 transition-colors cursor-pointer group">
                <input
                  type="checkbox"
                  {...register('categories.usefulness')}
                  disabled={isPending}
                  className="w-4 h-4 text-blue-600 bg-gray-700 border-gray-600 rounded focus:ring-blue-500 focus:ring-2 cursor-pointer"
                />
                <div className="flex-1">
                  <div className="text-sm font-medium text-white group-hover:text-blue-300 transition-colors">
                    Utilità
                  </div>
                  <div className="text-xs text-gray-500">
                    La risposta è utile per il mio caso specifico
                  </div>
                </div>
              </label>
            </div>
          </div>

          {/* Feedback Text */}
          <Textarea
            {...register('feedback_text')}
            label="Commento Dettagliato (opzionale)"
            placeholder="Descrivi la tua esperienza, suggerimenti per miglioramenti, o aspetti specifici che hai apprezzato o trovato problematici..."
            maxLength={2000}
            showCharCount
            rows={5}
            disabled={isPending}
            helperText="Il tuo feedback sarà utilizzato per migliorare il sistema RLCF"
          />

          {/* Character Count */}
          <div className="flex items-center justify-between text-xs text-gray-500">
            <span>
              Caratteri: {feedbackText?.length || 0} / 2000
            </span>
          </div>

          {/* Submit Button */}
          <div className="flex items-center justify-end gap-3 pt-4 border-t border-gray-700">
            <Button
              type="submit"
              disabled={rating === 0 || isPending}
              isLoading={isPending}
              className="min-w-[160px]"
            >
              {isPending ? (
                <>
                  <Loader className="w-4 h-4 mr-2 animate-spin" />
                  Invio...
                </>
              ) : (
                <>
                  <MessageSquarePlus className="w-4 h-4 mr-2" />
                  Invia Feedback
                </>
              )}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
