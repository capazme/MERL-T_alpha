/**
 * StarRating Component
 *
 * Interactive 5-star rating input component.
 * Supports hover preview and keyboard navigation.
 */

import { useState, forwardRef } from 'react';
import { Star } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface StarRatingProps {
  value?: number;
  onChange?: (rating: number) => void;
  maxRating?: number;
  size?: 'sm' | 'md' | 'lg';
  disabled?: boolean;
  readonly?: boolean;
  label?: string;
  error?: string;
  required?: boolean;
  showValue?: boolean;
}

const sizeMap = {
  sm: 'w-5 h-5',
  md: 'w-6 h-6',
  lg: 'w-8 h-8',
};

export const StarRating = forwardRef<HTMLDivElement, StarRatingProps>(
  (
    {
      value = 0,
      onChange,
      maxRating = 5,
      size = 'md',
      disabled = false,
      readonly = false,
      label,
      error,
      required = false,
      showValue = false,
    },
    ref
  ) => {
    const [hoverRating, setHoverRating] = useState<number | null>(null);

    const handleClick = (rating: number) => {
      if (!disabled && !readonly) {
        onChange?.(rating);
      }
    };

    const handleKeyDown = (e: React.KeyboardEvent, rating: number) => {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        handleClick(rating);
      }
    };

    const displayRating = hoverRating !== null ? hoverRating : value;

    return (
      <div ref={ref} className="space-y-2">
        {label && (
          <label className="block text-sm font-medium text-gray-300">
            {label}
            {required && <span className="text-red-400 ml-1">*</span>}
          </label>
        )}

        <div className="flex items-center gap-3">
          {/* Stars */}
          <div
            className="flex items-center gap-1"
            onMouseLeave={() => setHoverRating(null)}
            role="radiogroup"
            aria-label={label || 'Rating'}
          >
            {Array.from({ length: maxRating }, (_, index) => {
              const rating = index + 1;
              const isFilled = rating <= displayRating;

              return (
                <button
                  key={rating}
                  type="button"
                  onClick={() => handleClick(rating)}
                  onMouseEnter={() => !disabled && !readonly && setHoverRating(rating)}
                  onKeyDown={(e) => handleKeyDown(e, rating)}
                  disabled={disabled}
                  className={cn(
                    'transition-all duration-200',
                    'focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:ring-offset-gray-900 rounded',
                    !disabled && !readonly && 'cursor-pointer hover:scale-110',
                    disabled && 'cursor-not-allowed opacity-50'
                  )}
                  role="radio"
                  aria-checked={rating === value}
                  aria-label={`Rate ${rating} out of ${maxRating}`}
                >
                  <Star
                    className={cn(
                      sizeMap[size],
                      'transition-all duration-200',
                      isFilled
                        ? 'fill-yellow-400 text-yellow-400'
                        : 'fill-none text-gray-600 hover:text-gray-500'
                    )}
                  />
                </button>
              );
            })}
          </div>

          {/* Value Display */}
          {showValue && value > 0 && (
            <span className="text-sm font-medium text-gray-300 tabular-nums">
              {value.toFixed(1)} / {maxRating}
            </span>
          )}
        </div>

        {/* Error Message */}
        {error && <p className="text-sm text-red-400">{error}</p>}
      </div>
    );
  }
);

StarRating.displayName = 'StarRating';
