/**
 * Collapsible Component
 *
 * Accordion-style collapsible panel with smooth animations.
 * Supports controlled and uncontrolled modes.
 */

import { useState, useRef, useEffect, ReactNode } from 'react';
import { ChevronDown } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface CollapsibleProps {
  title: string | ReactNode;
  children: ReactNode;
  defaultOpen?: boolean;
  isOpen?: boolean;
  onOpenChange?: (isOpen: boolean) => void;
  disabled?: boolean;
  className?: string;
  contentClassName?: string;
  triggerClassName?: string;
  icon?: ReactNode;
  badge?: ReactNode;
}

export const Collapsible = ({
  title,
  children,
  defaultOpen = false,
  isOpen: controlledIsOpen,
  onOpenChange,
  disabled = false,
  className,
  contentClassName,
  triggerClassName,
  icon,
  badge,
}: CollapsibleProps) => {
  const [internalIsOpen, setInternalIsOpen] = useState(defaultOpen);
  const [height, setHeight] = useState<number | undefined>(defaultOpen ? undefined : 0);
  const contentRef = useRef<HTMLDivElement>(null);

  const isOpen = controlledIsOpen ?? internalIsOpen;

  const toggleOpen = () => {
    if (disabled) return;

    const newValue = !isOpen;

    if (controlledIsOpen === undefined) {
      setInternalIsOpen(newValue);
    }

    onOpenChange?.(newValue);
  };

  // Update height when isOpen changes
  useEffect(() => {
    if (!contentRef.current) return;

    if (isOpen) {
      const contentHeight = contentRef.current.scrollHeight;
      setHeight(contentHeight);
    } else {
      setHeight(0);
    }
  }, [isOpen, children]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      toggleOpen();
    }
  };

  return (
    <div className={cn('border border-gray-700 rounded-lg overflow-hidden', className)}>
      {/* Trigger */}
      <button
        type="button"
        onClick={toggleOpen}
        onKeyDown={handleKeyDown}
        disabled={disabled}
        className={cn(
          'w-full px-4 py-3 flex items-center justify-between gap-3',
          'bg-gray-800 hover:bg-gray-700 transition-colors',
          'focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-inset',
          disabled && 'opacity-50 cursor-not-allowed',
          triggerClassName
        )}
        aria-expanded={isOpen}
        aria-controls="collapsible-content"
      >
        <div className="flex items-center gap-3 flex-1 text-left">
          {icon && <span className="text-gray-400">{icon}</span>}
          <span className="text-white font-medium">{title}</span>
          {badge && <span>{badge}</span>}
        </div>

        <ChevronDown
          className={cn(
            'w-5 h-5 text-gray-400 transition-transform duration-200',
            isOpen && 'transform rotate-180'
          )}
        />
      </button>

      {/* Content */}
      <div
        ref={contentRef}
        id="collapsible-content"
        className={cn(
          'overflow-hidden transition-all duration-300 ease-in-out',
          contentClassName
        )}
        style={{ height: height !== undefined ? `${height}px` : 'auto' }}
        aria-hidden={!isOpen}
      >
        <div className="p-4 bg-gray-900 border-t border-gray-700">
          {children}
        </div>
      </div>
    </div>
  );
};

/**
 * CollapsibleGroup - For managing multiple collapsibles (accordion mode)
 */
interface CollapsibleGroupProps {
  children: ReactNode;
  allowMultiple?: boolean;
  defaultOpenIndexes?: number[];
  className?: string;
}

export const CollapsibleGroup = ({
  children,
  allowMultiple = false,
  defaultOpenIndexes = [],
  className,
}: CollapsibleGroupProps) => {
  const [openIndexes, setOpenIndexes] = useState<number[]>(defaultOpenIndexes);

  const handleToggle = (index: number) => {
    if (allowMultiple) {
      setOpenIndexes((prev) =>
        prev.includes(index) ? prev.filter((i) => i !== index) : [...prev, index]
      );
    } else {
      setOpenIndexes((prev) => (prev.includes(index) ? [] : [index]));
    }
  };

  return (
    <div className={cn('space-y-2', className)}>
      {Array.isArray(children) &&
        children.map((child, index) => {
          if (!child || typeof child !== 'object' || !('props' in child)) return child;

          return (
            <div key={index}>
              {typeof child === 'object' && 'props' in child
                ? {
                    ...child,
                    props: {
                      ...child.props,
                      isOpen: openIndexes.includes(index),
                      onOpenChange: () => handleToggle(index),
                    },
                  }
                : child}
            </div>
          );
        })}
    </div>
  );
};

/**
 * Usage Example:
 *
 * // Single collapsible
 * <Collapsible title="Click to expand">
 *   Content here
 * </Collapsible>
 *
 * // Accordion group (only one open at a time)
 * <CollapsibleGroup allowMultiple={false}>
 *   <Collapsible title="Section 1">Content 1</Collapsible>
 *   <Collapsible title="Section 2">Content 2</Collapsible>
 * </CollapsibleGroup>
 */
