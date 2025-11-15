import { createBrowserRouter, Navigate } from 'react-router-dom';
import { Layout } from '../../components/layouts/Layout';
import { AuthGuard } from '../../components/shared/AuthGuard';
import { ErrorBoundary } from '../../components/shared/ErrorBoundary';
import { Dashboard } from '../../features/dashboard/Dashboard';
import { TaskEvaluation } from '../../features/evaluation/TaskEvaluation';
import { Analytics } from '../../features/analytics/Analytics';
import { ConfigurationManager } from '../../features/admin/ConfigurationManager';
import { AdminDashboard } from '../../features/admin/AdminDashboard';
import { Login } from '../../features/auth/Login';
import { Leaderboard } from '../../features/analytics/Leaderboard';
import { AuthorityDashboard } from '../../features/dashboard/AuthorityDashboard';
import { AggregationViewer } from '../../features/analytics/AggregationViewer';
import { BiasAnalysisDashboard } from '../../features/analytics/BiasAnalysisDashboard';
import { ExportHub } from '../../features/export/ExportHub';
import { TaskAssignmentSystem } from '../../features/admin/TaskAssignmentSystem';
import { QueryMonitorDashboard } from '../../features/orchestration';
import { UserRole } from '@/types';

export const router = createBrowserRouter([
  {
    path: '/login',
    element: <Login />,
  },
  {
    path: '/',
    element: (
      <ErrorBoundary>
        <AuthGuard>
          <Layout />
        </AuthGuard>
      </ErrorBoundary>
    ),
    children: [
      {
        index: true,
        element: <Navigate to="/dashboard" replace />,
      },
      {
        path: 'dashboard',
        element: <Dashboard />,
      },
      {
        path: 'evaluation',
        children: [
          {
            index: true,
            element: <TaskEvaluation />,
          },
        ],
      },
      {
        path: 'analytics',
        children: [
          {
            index: true,
            element: <Analytics />,
          },
          {
            path: 'leaderboard',
            element: <Leaderboard />,
          },
          {
            path: 'authority',
            element: <AuthorityDashboard />,
          },
          {
            path: 'aggregation/:taskId',
            element: <AggregationViewer />,
          },
          {
            path: 'bias',
            element: <BiasAnalysisDashboard />,
          },
        ],
      },
      {
        path: 'admin',
        element: (
          <AuthGuard requiredRole={UserRole.ADMIN}>
            <AdminDashboard />
          </AuthGuard>
        ),
        children: [
          {
            path: 'settings',
            element: (
              <AuthGuard requiredRole={UserRole.ADMIN}>
                <ConfigurationManager />
              </AuthGuard>
            ),
          },
          {
            path: 'export',
            element: (
              <AuthGuard requiredRole={UserRole.ADMIN}>
                <ExportHub />
              </AuthGuard>
            ),
          },
          {
            path: 'assignments',
            element: (
              <AuthGuard requiredRole={UserRole.ADMIN}>
                <TaskAssignmentSystem />
              </AuthGuard>
            ),
          },
          {
            path: 'orchestration',
            element: (
              <AuthGuard requiredRole={UserRole.ADMIN}>
                <QueryMonitorDashboard />
              </AuthGuard>
            ),
          },
        ],
      },
    ],
  },
  {
    path: '*',
    element: <Navigate to="/dashboard" replace />,
  },
]);
