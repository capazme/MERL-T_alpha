import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';
import { formatDistanceToNow, format } from 'date-fns';
import { TaskType } from '../types/index';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function truncate(text: string, length: number) {
  if (text.length <= length) return text;
  return text.slice(0, length) + '...';
}

export function formatDate(date: string | Date) {
  const d = typeof date === 'string' ? new Date(date) : date;
  return format(d, 'PPP');
}

export function formatDateTime(date: string | Date) {
  const d = typeof date === 'string' ? new Date(date) : date;
  return format(d, 'PPP p');
}

export function formatRelativeTime(date: string | Date) {
  const d = typeof date === 'string' ? new Date(date) : date;
  return formatDistanceToNow(d, { addSuffix: true });
}

export function formatScore(score: number, decimals: number = 2) {
  return Number(score).toFixed(decimals);
}

export function formatPercentage(value: number, decimals: number = 1) {
  return `${(value * 100).toFixed(decimals)}%`;
}

export function getTaskTypeLabel(taskType: TaskType): string {
  const labels: Record<TaskType, string> = {
    [TaskType.QA]: 'Question & Answer',
    [TaskType.STATUTORY_RULE_QA]: 'Statutory Rule Q&A',
    [TaskType.CLASSIFICATION]: 'Classification',
    [TaskType.DRAFTING]: 'Legal Drafting',
    [TaskType.SUMMARIZATION]: 'Summarization',
    [TaskType.PREDICTION]: 'Outcome Prediction',
    [TaskType.NLI]: 'Natural Language Inference',
    [TaskType.NER]: 'Named Entity Recognition',
    [TaskType.RISK_SPOTTING]: 'Risk Spotting',
    [TaskType.DOCTRINE_APPLICATION]: 'Doctrine Application',
  };

  return labels[taskType] || taskType;
}

export function getTaskTypeColor(taskType: TaskType): string {
  const colors: Record<TaskType, string> = {
    [TaskType.QA]: 'bg-blue-500',
    [TaskType.STATUTORY_RULE_QA]: 'bg-cyan-500',
    [TaskType.CLASSIFICATION]: 'bg-green-500',
    [TaskType.DRAFTING]: 'bg-purple-500',
    [TaskType.SUMMARIZATION]: 'bg-orange-500',
    [TaskType.PREDICTION]: 'bg-red-500',
    [TaskType.NLI]: 'bg-indigo-500',
    [TaskType.NER]: 'bg-yellow-500',
    [TaskType.RISK_SPOTTING]: 'bg-rose-500',
    [TaskType.DOCTRINE_APPLICATION]: 'bg-pink-500',
  };

  return colors[taskType] || 'bg-gray-500';
}

export function getStatusColor(status: string): string {
  const colors: Record<string, string> = {
    'OPEN': 'bg-green-500 text-green-100',
    'BLIND_EVALUATION': 'bg-yellow-500 text-yellow-100',
    'AGGREGATED': 'bg-blue-500 text-blue-100',
    'CLOSED': 'bg-gray-500 text-gray-100',
  };
  
  return colors[status] || 'bg-gray-500 text-gray-100';
}

export function getAuthorityTrend(current: number, previous: number): 'up' | 'down' | 'stable' {
  if (current > previous) return 'up';
  if (current < previous) return 'down';
  return 'stable';
}

export function calculatePercentile(score: number, allScores: number[]): number {
  if (allScores.length === 0) return 0;
  
  const sorted = allScores.sort((a, b) => a - b);
  const index = sorted.findIndex(s => s >= score);
  
  if (index === -1) return 100;
  return Math.round((index / sorted.length) * 100);
}

export function debounce<T extends (...args: any[]) => any>(
  func: T,
  delay: number
): (...args: Parameters<T>) => void {
  let timeoutId: NodeJS.Timeout;
  
  return (...args: Parameters<T>) => {
    clearTimeout(timeoutId);
    timeoutId = setTimeout(() => func(...args), delay);
  };
}

export function generateId(): string {
  return Date.now().toString(36) + Math.random().toString(36).substr(2);
}

export function isValidEmail(email: string): boolean {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email);
}

export function copyToClipboard(text: string): Promise<void> {
  if (navigator.clipboard) {
    return navigator.clipboard.writeText(text);
  }
  
  // Fallback for older browsers
  return new Promise((resolve, reject) => {
    const textArea = document.createElement('textarea');
    textArea.value = text;
    textArea.style.position = 'absolute';
    textArea.style.left = '-999999px';
    
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();
    
    try {
      document.execCommand('copy');
      document.body.removeChild(textArea);
      resolve();
    } catch (error) {
      document.body.removeChild(textArea);
      reject(error);
    }
  });
}

export function downloadJson(data: any, filename: string): void {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  
  const link = document.createElement('a');
  link.href = url;
  link.download = filename.endsWith('.json') ? filename : `${filename}.json`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  
  URL.revokeObjectURL(url);
}

export function sleep(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}