/**
 * Textarea Component
 *
 * Multi-line text input with auto-resize capability.
 * Supports character counting and validation states.
 */

import { forwardRef, TextareaHTMLAttributes, useState, useEffect } from 'react';
import { cn } from '@/lib/utils';

export interface TextareaProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  error?: string;
  helperText?: string;
  showCharCount?: boolean;
  maxLength?: number;
  autoResize?: boolean;
}

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaProps>(
  (
    {
      className,
      label,
      error,
      helperText,
      showCharCount = false,
      maxLength,
      autoResize = false,
      onChange,
      value,
      ...props
    },
    ref
  ) => {
    const [charCount, setCharCount] = useState(0);

    useEffect(() => {
      if (value !== undefined) {
        setCharCount(String(value).length);
      }
    }, [value]);

    const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
      setCharCount(e.target.value.length);
      onChange?.(e);
    };

    return (
      <div className="w-full space-y-2">
        {label && (
          <label className="block text-sm font-medium text-gray-300">
            {label}
            {props.required && <span className="text-red-400 ml-1">*</span>}
          </label>
        )}

        <textarea
          ref={ref}
          className={cn(
            'w-full px-4 py-3 bg-gray-800 border rounded-lg',
            'text-white placeholder-gray-500',
            'focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent',
            'disabled:opacity-50 disabled:cursor-not-allowed',
            'transition-all duration-200',
            autoResize && 'resize-none overflow-hidden',
            !autoResize && 'resize-y',
            error
              ? 'border-red-500 focus:ring-red-500'
              : 'border-gray-700 hover:border-gray-600',
            className
          )}
          onChange={handleChange}
          value={value}
          maxLength={maxLength}
          style={
            autoResize
              ? {
                  minHeight: '80px',
                  height: 'auto',
                  maxHeight: '400px',
                }
              : undefined
          }
          {...props}
        />

        {/* Footer: Error, Helper Text, or Character Count */}
        <div className="flex items-center justify-between text-sm">
          <div className="flex-1">
            {error && <p className="text-red-400">{error}</p>}
            {!error && helperText && <p className="text-gray-400">{helperText}</p>}
          </div>

          {showCharCount && maxLength && (
            <p
              className={cn(
                'text-xs tabular-nums',
                charCount > maxLength * 0.9
                  ? 'text-orange-400'
                  : charCount === maxLength
                  ? 'text-red-400'
                  : 'text-gray-500'
              )}
            >
              {charCount} / {maxLength}
            </p>
          )}
        </div>
      </div>
    );
  }
);

Textarea.displayName = 'Textarea';
