import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { authService, type UserProfile } from '../services/authService';

interface AuthStore {
  isAuthenticated: boolean;
  user: UserProfile | null;
  accessToken: string | null;
  refreshToken: string | null;
  trialLeftDays: number | null;
  isTrialActive: boolean;

  setAuth: (user: UserProfile, accessToken: string, refreshToken: string) => void;
  setUser: (user: UserProfile) => void;
  updateAccessToken: (accessToken: string) => void;
  logout: () => void;

  canAccessSport: (sport: string) => boolean;
  canAccessFullReasoning: () => boolean;
  canAccessFullVoting: () => boolean;
  canAccessHistoryDays: (days: number) => boolean;

  initializeAuth: () => Promise<void>;
}

export const usePlanStore = create<AuthStore>()(persist((set, get) => ({
  isAuthenticated: false,
  user: null,
  accessToken: null,
  refreshToken: null,
  trialLeftDays: null,
  isTrialActive: false,

  setAuth: (user, accessToken, refreshToken) => {
    set({
      isAuthenticated: true,
      user,
      accessToken,
      refreshToken,
    });
  },

  setUser: (user) => {
    set({ user });
  },

  updateAccessToken: (accessToken) => {
    set({ accessToken });
  },

  logout: async () => {
    const { refreshToken } = get();
    if (refreshToken) {
      try {
        await authService.logout(refreshToken);
      } catch (error) {
        console.error('Logout error:', error);
      }
    }
    set({
      isAuthenticated: false,
      user: null,
      accessToken: null,
      refreshToken: null,
      trialLeftDays: null,
      isTrialActive: false,
    });
  },

  canAccessSport: (sport) => {
    const { user } = get();
    if (!user) return false;
    if (user.plan_type === 'pro' || user.plan_type === 'partner') return true;
    return sport === 'soccer';
  },

  canAccessFullReasoning: () => {
    const { user } = get();
    return user?.plan_type === 'pro' || user?.plan_type === 'partner';
  },

  canAccessFullVoting: () => {
    const { user } = get();
    return user?.plan_type === 'pro' || user?.plan_type === 'partner';
  },

  canAccessHistoryDays: (days) => {
    const { user } = get();
    if (!user) return false;
    if (user.plan_type === 'pro' || user.plan_type === 'partner') return true;
    return days <= 3;
  },

  initializeAuth: async () => {
    const { refreshToken, accessToken } = get();

    if (refreshToken && accessToken) {
      try {
        const meData = await authService.getMe(accessToken);
        set({
          isAuthenticated: true,
          user: meData.user,
          trialLeftDays: meData.trial_left_days,
          isTrialActive: meData.is_trial_active,
        });
      } catch (error) {
        try {
          const refreshData = await authService.refreshAccessToken(refreshToken);
          set({ accessToken: refreshData.access_token });

          const meData = await authService.getMe(refreshData.access_token);
          set({
            isAuthenticated: true,
            user: meData.user,
            trialLeftDays: meData.trial_left_days,
            isTrialActive: meData.is_trial_active,
          });
        } catch (refreshError) {
          set({
            isAuthenticated: false,
            user: null,
            accessToken: null,
            refreshToken: null,
          });
        }
      }
    }
  },
}), {
  name: 'oraculum-auth',
}));
