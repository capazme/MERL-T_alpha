/**
 * NER Correction Form Component
 *
 * Allows users to submit corrections to Named Entity Recognition (NER):
 * - ADD_ENTITY: Add missing entity
 * - REMOVE_ENTITY: Remove incorrectly identified entity
 * - CORRECT_TYPE: Fix entity type classification
 * - CORRECT_SPAN: Adjust entity boundaries
 */

import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Card, CardHeader, CardTitle, CardContent } from '@components/ui/Card';
import { Button } from '@components/ui/Button';
import { Textarea } from '@components/ui/Textarea';
import { Select, type SelectOption } from '@components/ui/Select';
import { Badge } from '@components/ui/Badge';
import { useSubmitNerCorrection } from '@hooks/useOrchestration';
import {
  Tag,
  Plus,
  Trash2,
  Edit3,
  MoveHorizontal,
  CheckCircle,
  Loader,
  Info,
} from 'lucide-react';
import type { NERCorrectionRequest } from '@/types/orchestration';

const ENTITY_TYPE_OPTIONS: SelectOption[] = [
  { value: 'NORMA', label: 'Norma (Legge, Decreto, ecc.)' },
  { value: 'ARTICOLO', label: 'Articolo di Legge' },
  { value: 'SENTENZA', label: 'Sentenza/Giurisprudenza' },
  { value: 'ISTITUZIONE', label: 'Istituzione (Corte, Tribunale)' },
  { value: 'CONCETTO_GIURIDICO', label: 'Concetto Giuridico' },
  { value: 'SOGGETTO', label: 'Soggetto (Persona, Società)' },
  { value: 'DATA', label: 'Data' },
  { value: 'LUOGO', label: 'Luogo' },
  { value: 'ALTRO', label: 'Altro' },
];

const CORRECTION_TYPE_OPTIONS: SelectOption[] = [
  { value: 'ADD_ENTITY', label: 'Aggiungi Entità Mancante' },
  { value: 'REMOVE_ENTITY', label: 'Rimuovi Entità Errata' },
  { value: 'CORRECT_TYPE', label: 'Correggi Tipo Entità' },
  { value: 'CORRECT_SPAN', label: 'Correggi Confini Entità' },
];

// Validation schema (note: reasoning not sent to backend, just for UX)
const nerCorrectionSchema = z.object({
  correction_type: z.enum(['ADD_ENTITY', 'REMOVE_ENTITY', 'CORRECT_TYPE', 'CORRECT_SPAN']),
  entity_text: z.string().min(1, 'Specifica il testo dell\'entità').max(500),
  entity_type: z.string().min(1, 'Seleziona il tipo di entità'),
  start_offset: z.number().int().min(0).optional(),
  end_offset: z.number().int().min(0).optional(),
  correct_entity_type: z.string().optional(),
  reasoning: z.string().min(20, 'Fornisci una motivazione di almeno 20 caratteri').max(1000).optional(),
});

type NERCorrectionFormData = z.infer<typeof nerCorrectionSchema>;

interface NERCorrectionFormProps {
  traceId: string;
  queryText: string;
  onSuccess?: () => void;
}

export function NERCorrectionForm({ traceId, queryText, onSuccess }: NERCorrectionFormProps) {
  const [correctionType, setCorrectionType] = useState<string>('');
  const [submitted, setSubmitted] = useState(false);
  const [highlightedText, setHighlightedText] = useState<string>('');

  const { mutate: submitCorrection, isPending } = useSubmitNerCorrection();

  const {
    register,
    handleSubmit,
    formState: { errors },
    watch,
    setValue,
    reset,
  } = useForm<NERCorrectionFormData>({
    resolver: zodResolver(nerCorrectionSchema),
    mode: 'onChange',
    defaultValues: {
      correction_type: undefined,
      entity_text: '',
      entity_type: '',
      start_offset: undefined,
      end_offset: undefined,
      correct_entity_type: '',
      reasoning: '',
    },
  });

  const selectedCorrectionType = watch('correction_type');
  const entityType = watch('entity_type');

  const handleTextSelection = () => {
    const selection = window.getSelection();
    if (selection && selection.toString().trim().length > 0) {
      const selectedText = selection.toString().trim();
      setHighlightedText(selectedText);
      setValue('entity_text', selectedText);

      // Calculate offsets
      const range = selection.getRangeAt(0);
      const startOffset = range.startOffset;
      const endOffset = range.endOffset;
      setValue('start_offset', startOffset);
      setValue('end_offset', endOffset);
    }
  };

  const onSubmit = (data: NERCorrectionFormData) => {
    const correctionData: any = {
      entity_text: data.entity_text,
      entity_type: data.entity_type,
    };

    if (data.correction_type === 'ADD_ENTITY') {
      correctionData.start_offset = data.start_offset;
      correctionData.end_offset = data.end_offset;
    } else if (data.correction_type === 'CORRECT_TYPE') {
      correctionData.correct_entity_type = data.correct_entity_type;
    } else if (data.correction_type === 'CORRECT_SPAN') {
      correctionData.correct_start_offset = data.start_offset;
      correctionData.correct_end_offset = data.end_offset;
    }

    const correctionRequest: NERCorrectionRequest = {
      trace_id: traceId,
      correction_type: data.correction_type,
      correction_data: correctionData,
    };

    submitCorrection(correctionRequest, {
      onSuccess: () => {
        setSubmitted(true);
        setTimeout(() => {
          reset();
          setCorrectionType('');
          setHighlightedText('');
          setSubmitted(false);
          onSuccess?.();
        }, 3000);
      },
      onError: (error: any) => {
        console.error('Failed to submit NER correction:', error);
      },
    });
  };

  const getCorrectionIcon = (type: string) => {
    switch (type) {
      case 'ADD_ENTITY':
        return <Plus className="w-5 h-5" />;
      case 'REMOVE_ENTITY':
        return <Trash2 className="w-5 h-5" />;
      case 'CORRECT_TYPE':
        return <Edit3 className="w-5 h-5" />;
      case 'CORRECT_SPAN':
        return <MoveHorizontal className="w-5 h-5" />;
      default:
        return <Tag className="w-5 h-5" />;
    }
  };

  // Success state
  if (submitted) {
    return (
      <Card className="border-green-500/30">
        <CardContent className="py-12 text-center">
          <CheckCircle className="w-16 h-16 text-green-400 mx-auto mb-4" />
          <h3 className="text-xl font-semibold text-white mb-2">
            Correzione NER Inviata!
          </h3>
          <p className="text-gray-400 max-w-md mx-auto">
            Grazie per il tuo contributo. Le correzioni NER migliorano l'accuratezza del sistema
            di riconoscimento entità attraverso feedback iterativo.
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <Tag className="w-5 h-5 text-orange-400" />
          Correzioni NER (Named Entity Recognition)
        </CardTitle>
        <p className="text-sm text-gray-400 mt-2">
          Segnala errori nell'identificazione di entità legali (norme, articoli, sentenze, ecc.)
        </p>
      </CardHeader>

      <CardContent>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
          {/* Query Text Display with Selection */}
          <div className="space-y-2">
            <label className="block text-sm font-medium text-gray-300">Query Originale</label>
            <div
              className="p-4 bg-gray-800 rounded-lg border border-gray-700 text-gray-300 leading-relaxed select-text cursor-text"
              onMouseUp={handleTextSelection}
            >
              {queryText}
            </div>
            <div className="flex items-start gap-2 text-xs text-gray-500">
              <Info className="w-3.5 h-3.5 mt-0.5 flex-shrink-0" />
              <p>
                Seleziona il testo nella query per identificare l'entità. Il testo evidenziato
                verrà automaticamente inserito nel campo "Testo Entità".
              </p>
            </div>
            {highlightedText && (
              <div className="mt-2">
                <Badge variant="outline" className="text-blue-300 border-blue-500/40">
                  Testo selezionato: "{highlightedText}"
                </Badge>
              </div>
            )}
          </div>

          {/* Correction Type */}
          <Select
            label={
              <span>
                Tipo di Correzione <span className="text-red-400">*</span>
              </span>
            }
            options={CORRECTION_TYPE_OPTIONS}
            value={selectedCorrectionType || ''}
            onChange={(value) => {
              setCorrectionType(value);
              setValue('correction_type', value as any);
            }}
            placeholder="Seleziona il tipo di correzione"
          />

          {/* Dynamic fields based on correction type */}
          {selectedCorrectionType && (
            <div className="p-4 bg-orange-500/10 border border-orange-500/30 rounded-lg">
              <div className="flex items-start gap-3 mb-3">
                {getCorrectionIcon(selectedCorrectionType)}
                <div className="flex-1">
                  <h4 className="text-sm font-semibold text-white">
                    {CORRECTION_TYPE_OPTIONS.find((opt) => opt.value === selectedCorrectionType)?.label}
                  </h4>
                  <p className="text-xs text-gray-400 mt-1">
                    {selectedCorrectionType === 'ADD_ENTITY' &&
                      'Aggiungi un\'entità non rilevata dal sistema NER'}
                    {selectedCorrectionType === 'REMOVE_ENTITY' &&
                      'Rimuovi un\'entità erroneamente identificata'}
                    {selectedCorrectionType === 'CORRECT_TYPE' &&
                      'Correggi la classificazione di un\'entità (es. da SENTENZA a NORMA)'}
                    {selectedCorrectionType === 'CORRECT_SPAN' &&
                      'Correggi i confini di un\'entità (es. "Art. 2043 CC" invece di "Art. 2043")'}
                  </p>
                </div>
              </div>

              <div className="space-y-4 mt-4">
                {/* Entity Text */}
                <Textarea
                  {...register('entity_text')}
                  label={
                    <span>
                      Testo dell'Entità <span className="text-red-400">*</span>
                    </span>
                  }
                  placeholder="Es: Art. 2043 Codice Civile"
                  maxLength={500}
                  rows={2}
                  disabled={isPending}
                  error={errors.entity_text?.message}
                  helperText="Il testo esatto dell'entità nella query (puoi selezionarlo sopra)"
                />

                {/* Entity Type */}
                {selectedCorrectionType !== 'CORRECT_TYPE' && (
                  <Select
                    label={
                      <span>
                        Tipo di Entità <span className="text-red-400">*</span>
                      </span>
                    }
                    options={ENTITY_TYPE_OPTIONS}
                    value={entityType || ''}
                    onChange={(value) => setValue('entity_type', value)}
                    placeholder="Seleziona il tipo di entità"
                  />
                )}

                {/* Correct Entity Type (for CORRECT_TYPE) */}
                {selectedCorrectionType === 'CORRECT_TYPE' && (
                  <>
                    <Select
                      label={
                        <span>
                          Tipo Attuale (Errato) <span className="text-red-400">*</span>
                        </span>
                      }
                      options={ENTITY_TYPE_OPTIONS}
                      value={entityType || ''}
                      onChange={(value) => setValue('entity_type', value)}
                      placeholder="Tipo attualmente assegnato"
                    />
                    <Select
                      label={
                        <span>
                          Tipo Corretto <span className="text-red-400">*</span>
                        </span>
                      }
                      options={ENTITY_TYPE_OPTIONS}
                      value={watch('correct_entity_type') || ''}
                      onChange={(value) => setValue('correct_entity_type', value)}
                      placeholder="Tipo che dovrebbe essere"
                    />
                  </>
                )}
              </div>
            </div>
          )}

          {/* Reasoning */}
          {selectedCorrectionType && (
            <Textarea
              {...register('reasoning')}
              label={
                <span>
                  Motivazione <span className="text-red-400">*</span>
                </span>
              }
              placeholder="Spiega perché questa correzione è necessaria. Es: 'L'Art. 2043 CC è una norma fondamentale sulla responsabilità extracontrattuale e doveva essere riconosciuto come NORMA, non come CONCETTO_GIURIDICO'"
              maxLength={1000}
              showCharCount
              rows={4}
              disabled={isPending}
              error={errors.reasoning?.message}
              helperText="Minimo 20 caratteri. Fornisci una spiegazione chiara della correzione"
            />
          )}

          {/* Submit Button */}
          <div className="flex items-center justify-end gap-3 pt-4 border-t border-gray-700">
            <Button
              type="submit"
              disabled={!selectedCorrectionType || isPending}
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
                  <Tag className="w-4 h-4 mr-2" />
                  Invia Correzione
                </>
              )}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  );
}
