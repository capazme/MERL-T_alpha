/**
 * Query Validation Schemas
 *
 * Zod schemas for query form validation.
 * Aligned with backend constraints from QueryRequest Pydantic schema.
 */

import { z } from 'zod';

/**
 * Query form validation schema
 * Backend constraint: min_length=10, max_length=2000
 */
export const queryFormSchema = z.object({
  query: z
    .string()
    .min(10, 'La query deve contenere almeno 10 caratteri')
    .max(2000, 'La query non può superare 2000 caratteri')
    .trim()
    .refine((val) => val.length >= 10, {
      message: 'La query non può essere composta solo da spazi',
    }),
});

/**
 * Query context validation schema
 */
export const queryContextSchema = z.object({
  temporal_reference: z.string().optional().nullable(),
  jurisdiction: z
    .enum(['nazionale', 'regionale', 'comunitario'])
    .default('nazionale'),
  user_role: z
    .enum(['cittadino', 'avvocato', 'giudice', 'studente'])
    .default('cittadino'),
  previous_queries: z.array(z.string()).optional().nullable(),
});

/**
 * Query options validation schema
 * Backend constraints: max_iterations (1-10), timeout_ms (1000-120000)
 */
export const queryOptionsSchema = z.object({
  max_iterations: z
    .number()
    .int()
    .min(1, 'Minimo 1 iterazione')
    .max(10, 'Massimo 10 iterazioni')
    .default(3),
  timeout_ms: z
    .number()
    .int()
    .min(10000, 'Timeout minimo 10 secondi')
    .max(120000, 'Timeout massimo 120 secondi')
    .default(30000),
  return_trace: z.boolean().default(true),
  stream_response: z.boolean().default(false),
});

/**
 * Type inference for form data
 */
export type QueryFormData = z.infer<typeof queryFormSchema>;
export type QueryContextData = z.infer<typeof queryContextSchema>;
export type QueryOptionsData = z.infer<typeof queryOptionsSchema>;
