import { z } from 'zod';
import type { FieldErrors, UseFormRegister } from 'react-hook-form';

export const preferenceSchema = z.object({
  preference: z.enum(['A', 'B', 'tie'], {
    message: 'You must select a preference.'
  }),
  reasoning: z.string().min(30, 'Please provide a detailed reason for your choice (min 30 chars).'),
});

interface PreferenceFormProps {
  register: UseFormRegister<any>;
  errors: FieldErrors<any>;
}

export function PreferenceForm({ register, errors }: PreferenceFormProps) {
  return (
    <div className="space-y-6">
      <div>
        <label className="block text-sm font-medium text-slate-300 mb-2">Which response is better?</label>
        <div className="flex flex-col sm:flex-row gap-3 rounded-lg bg-slate-900 p-2">
          <label className="flex-1 cursor-pointer p-3 text-center rounded-md border-2 border-transparent transition-all has-[:checked]:border-blue-500 has-[:checked]:bg-blue-900/50">
            <input type="radio" value="A" className="sr-only" {...register('preference')} />
            <span className="text-lg font-bold text-blue-400">Response A is better</span>
          </label>
          <label className="flex-1 cursor-pointer p-3 text-center rounded-md border-2 border-transparent transition-all has-[:checked]:border-green-500 has-[:checked]:bg-green-900/50">
            <input type="radio" value="B" className="sr-only" {...register('preference')} />
            <span className="text-lg font-bold text-green-400">Response B is better</span>
          </label>
          <label className="flex-1 cursor-pointer p-3 text-center rounded-md border-2 border-transparent transition-all has-[:checked]:border-slate-500 has-[:checked]:bg-slate-700/50">
            <input type="radio" value="tie" className="sr-only" {...register('preference')} />
            <span className="text-lg font-bold text-slate-400">They are about the same</span>
          </label>
        </div>
        {errors.preference && <p className="text-red-400 text-xs mt-1">{String(errors.preference.message)}</p>}
      </div>

      <div>
        <label htmlFor="reasoning" className="block text-sm font-medium text-slate-300 mb-2">Why?</label>
        <textarea
          id="reasoning"
          rows={6}
          className="w-full p-3 bg-slate-900 border border-slate-700 rounded-md focus:ring-2 focus:ring-violet-500"
          placeholder="Explain your preference. For example: 'Response A is more concise and directly answers the question, while Response B includes irrelevant information.'"
          {...register('reasoning')}
        />
        {errors.reasoning && <p className="text-red-400 text-xs mt-1">{String(errors.reasoning.message)}</p>}
      </div>
    </div>
  );
}
