import { QueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutes
      gcTime: 10 * 60 * 1000, // 10 minutes (formerly cacheTime)
      retry: (failureCount, error: any) => {
        // Don't retry on 4xx errors except 408, 429
        if (error?.response?.status >= 400 && error?.response?.status < 500) {
          return error?.response?.status === 408 || error?.response?.status === 429;
        }
        return failureCount < 3;
      },
      retryDelay: (attemptIndex) => Math.min(1000 * 2 ** attemptIndex, 30000),
    },
    mutations: {
      retry: 1,
      onError: (error: any) => {
        const message = error?.response?.data?.message || error?.message || 'An error occurred';
        toast.error(message);
      },
    },
  },
});

// Global error handler
queryClient.setMutationDefaults(['submit-feedback'], {
  onSuccess: () => {
    toast.success('Feedback submitted successfully!');
    // Invalidate relevant queries
    queryClient.invalidateQueries({ queryKey: ['tasks'] });
    queryClient.invalidateQueries({ queryKey: ['feedback'] });
    queryClient.invalidateQueries({ queryKey: ['user-performance'] });
  },
});

queryClient.setMutationDefaults(['update-task-status'], {
  onSuccess: () => {
    toast.success('Task status updated!');
    queryClient.invalidateQueries({ queryKey: ['tasks'] });
    queryClient.invalidateQueries({ queryKey: ['analytics'] });
  },
});

queryClient.setMutationDefaults(['update-config'], {
  onSuccess: () => {
    toast.success('Configuration updated!');
    queryClient.invalidateQueries({ queryKey: ['config'] });
  },
});