import React, { type ErrorInfo, type ReactNode } from 'react';
import { AlertTriangle, RefreshCw, Home, Bug } from 'lucide-react';
import { Button } from '../ui/Button';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/Card';

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
  errorInfo: ErrorInfo | null;
}

interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: ReactNode;
  onError?: (error: Error, errorInfo: ErrorInfo) => void;
  showErrorDetails?: boolean;
}

export class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
    };
  }

  static getDerivedStateFromError(error: Error): Partial<ErrorBoundaryState> {
    return {
      hasError: true,
      error,
    };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('ErrorBoundary caught an error:', error, errorInfo);
    
    this.setState({
      error,
      errorInfo,
    });

    // Call the onError callback if provided
    this.props.onError?.(error, errorInfo);

    // In a real app, you might want to log this to an error reporting service
    // like Sentry, LogRocket, etc.
  }

  handleRetry = () => {
    this.setState({
      hasError: false,
      error: null,
      errorInfo: null,
    });
  };

  handleGoHome = () => {
    window.location.href = '/';
  };

  render() {
    if (this.state.hasError) {
      // Use custom fallback if provided
      if (this.props.fallback) {
        return this.props.fallback;
      }

      // Default error UI
      return (
        <div className="min-h-screen flex items-center justify-center bg-slate-900 p-4">
          <Card className="w-full max-w-lg">
            <CardHeader>
              <CardTitle className="flex items-center gap-3 text-red-400">
                <AlertTriangle className="h-6 w-6" />
                Something went wrong
              </CardTitle>
            </CardHeader>
            
            <CardContent className="space-y-6">
              <div className="text-slate-300">
                <p className="mb-4">
                  We're sorry, but something unexpected happened. The error has been logged
                  and our team has been notified.
                </p>
                
                {this.props.showErrorDetails && this.state.error && (
                  <details className="mt-4">
                    <summary className="cursor-pointer text-sm font-medium text-slate-400 hover:text-slate-300">
                      Technical Details
                    </summary>
                    <div className="mt-3 p-3 bg-slate-800 rounded-md border border-slate-700">
                      <div className="text-xs text-red-400 font-mono">
                        <div className="mb-2">
                          <strong>Error:</strong> {this.state.error.message}
                        </div>
                        <div className="mb-2">
                          <strong>Stack:</strong>
                        </div>
                        <pre className="whitespace-pre-wrap text-xs overflow-auto max-h-32">
                          {this.state.error.stack}
                        </pre>
                        {this.state.errorInfo && (
                          <div className="mt-2">
                            <strong>Component Stack:</strong>
                            <pre className="whitespace-pre-wrap text-xs overflow-auto max-h-24">
                              {this.state.errorInfo.componentStack}
                            </pre>
                          </div>
                        )}
                      </div>
                    </div>
                  </details>
                )}
              </div>

              <div className="flex flex-col sm:flex-row gap-3">
                <Button
                  onClick={this.handleRetry}
                  className="flex-1"
                  variant="default"
                >
                  <RefreshCw className="mr-2 h-4 w-4" />
                  Try Again
                </Button>
                
                <Button
                  onClick={this.handleGoHome}
                  variant="secondary"
                  className="flex-1"
                >
                  <Home className="mr-2 h-4 w-4" />
                  Go Home
                </Button>
              </div>

              <div className="text-center">
                <p className="text-xs text-slate-500">
                  If this problem persists, please contact support with the error details above.
                </p>
              </div>
            </CardContent>
          </Card>
        </div>
      );
    }

    return this.props.children;
  }
}

// Hook-based error boundary for functional components
export function useErrorHandler() {
  return (error: Error, errorInfo?: ErrorInfo) => {
    console.error('Error caught by useErrorHandler:', error, errorInfo);
    
    // You could integrate with error reporting service here
    // For now, just re-throw to be caught by nearest error boundary
    throw error;
  };
}

// Simple error fallback components
export function SimpleErrorFallback({ 
  error, 
  resetError 
}: { 
  error: Error; 
  resetError: () => void;
}) {
  return (
    <div className="p-6 text-center">
      <div className="mb-4">
        <Bug className="h-12 w-12 text-red-400 mx-auto mb-3" />
        <h3 className="text-lg font-semibold text-white mb-2">Oops! Something went wrong</h3>
        <p className="text-slate-400 text-sm">{error.message}</p>
      </div>
      <Button onClick={resetError} size="sm">
        <RefreshCw className="mr-2 h-4 w-4" />
        Try again
      </Button>
    </div>
  );
}

// Loading fallback component
export function LoadingFallback({ 
  message = 'Loading...' 
}: { 
  message?: string;
}) {
  return (
    <div className="flex items-center justify-center p-8">
      <div className="text-center">
        <div className="animate-spin h-8 w-8 border-2 border-violet-500 border-t-transparent rounded-full mx-auto mb-3"></div>
        <p className="text-slate-400 text-sm">{message}</p>
      </div>
    </div>
  );
}

// Empty state fallback component
export function EmptyStateFallback({ 
  message = 'No data available',
  action
}: { 
  message?: string;
  action?: ReactNode;
}) {
  return (
    <div className="text-center p-8">
      <div className="mb-4">
        <div className="h-12 w-12 bg-slate-700 rounded-full mx-auto mb-3 flex items-center justify-center">
          <div className="h-6 w-6 border-2 border-slate-500 rounded"></div>
        </div>
        <p className="text-slate-400">{message}</p>
      </div>
      {action && <div>{action}</div>}
    </div>
  );
}