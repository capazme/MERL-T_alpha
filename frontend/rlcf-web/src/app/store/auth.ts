import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import type { User } from '../../types/index';
import { UserRole } from '../../types/index';
import { apiClient } from '../../lib/api';

interface AuthState {
  user: User | null;
  token: string | null;
  role: UserRole;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
}

interface AuthActions {
  login: (user: User) => void;
  logout: () => void;
  refreshUser: () => Promise<void>;
  updateUser: (updates: Partial<User>) => void;
  clearError: () => void;
  setRole: (role: UserRole) => void;
}

type AuthStore = AuthState & AuthActions;

export const useAuthStore = create<AuthStore>()(
  persist(
    (set, get) => ({
      // Initial state
      user: null,
      token: null,
      role: UserRole.VIEWER,
      isAuthenticated: false,
      isLoading: false,
      error: null,

      // Actions
      login: (user) => {
        const role = determineUserRole(user);
        const token = 'supersecretkey'; // Use RLCF API key
        localStorage.setItem('auth_token', token);
        apiClient.setApiKey(token);
        
        set({
          user,
          token,
          isAuthenticated: true,
          isLoading: false,
          error: null,
          role,
        });
      },

      logout: () => {
        localStorage.removeItem('auth_token');
        apiClient.setApiKey(null);
        
        set({
          user: null,
          token: null,
          isAuthenticated: false,
          role: UserRole.VIEWER,
          error: null,
        });
      },

      refreshUser: async () => {
        const token = localStorage.getItem('auth_token');
        if (!token || token !== 'supersecretkey') {
          get().logout();
          return;
        }

        // For now, just keep the user logged in if token exists
        // In a real implementation, we'd verify the token with the backend
        if (!get().user) {
          // If no user in state but valid token, restore default admin user
          set({
            user: {
              id: 1,
              username: 'admin',
              email: 'admin@rlcf.ai',
              authority_score: 0.95,
              track_record_score: 0.9,
              baseline_credential_score: 0.8
            },
            token,
            isAuthenticated: true,
            isLoading: false,
            role: UserRole.ADMIN,
          });
        }
      },

      updateUser: (updates) => {
        const currentUser = get().user;
        if (currentUser) {
          const updatedUser = { ...currentUser, ...updates };
          set({ 
            user: updatedUser,
            role: determineUserRole(updatedUser),
          });
        }
      },

      clearError: () => set({ error: null }),

      setRole: (role) => set({ role }),
    }),
    {
      name: 'auth-store',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        token: state.token,
        role: state.role,
      }),
    }
  )
);

// Helper function to determine user role based on authority score and credentials
function determineUserRole(user: User): UserRole {
  // Determine role based on authority score and user characteristics
  // Admin users typically have very high authority and system access
  if (user.username === 'admin' || user.authority_score >= 0.9) {
    return UserRole.ADMIN;
  }
  
  // Evaluators are users with good authority scores who can evaluate tasks
  if (user.authority_score >= 0.4) {
    return UserRole.EVALUATOR;
  }
  
  // Everyone else is a viewer
  return UserRole.VIEWER;
}

// Initialize auth state on app load
export const initializeAuth = () => {
  const token = localStorage.getItem('auth_token');
  if (token) {
    useAuthStore.getState().refreshUser();
  }
};