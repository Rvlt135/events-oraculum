import { create } from 'zustand';
import { persist } from 'zustand/middleware';

type PlanType = 'free' | 'pro';

interface User {
  isAuthenticated: boolean;
  email?: string;
  plan: PlanType;
  trialEndsAt: Date | null;
}

interface PlanStore extends User {
  login: (email: string, plan?: PlanType) => void;
  logout: () => void;
  setPlan: (plan: PlanType) => void;
  canAccessSport: (sport: string) => boolean;
  canAccessFullReasoning: () => boolean;
  canAccessFullVoting: () => boolean;
  canAccessHistoryDays: (days: number) => boolean;
}

export const usePlanStore = create<PlanStore>()(persist((set, get) => ({
  isAuthenticated: false,
  email: undefined,
  plan: 'free',
  trialEndsAt: null,

  login: (email, plan = 'free') => {
    const trialEndsAt = plan === 'free' ? new Date(Date.now() + 7 * 24 * 60 * 60 * 1000) : null;
    set({ isAuthenticated: true, email, plan, trialEndsAt });
  },

  logout: () => set({ isAuthenticated: false, email: undefined, plan: 'free', trialEndsAt: null }),

  setPlan: (plan) => {
    const trialEndsAt = plan === 'free' ? new Date(Date.now() + 7 * 24 * 60 * 60 * 1000) : null;
    set({ plan, trialEndsAt });
  },

  canAccessSport: (sport) => {
    const { plan } = get();
    if (plan === 'pro') return true;
    return sport === 'soccer';
  },

  canAccessFullReasoning: () => {
    const { plan } = get();
    return plan === 'pro';
  },

  canAccessFullVoting: () => {
    const { plan } = get();
    return plan === 'pro';
  },

  canAccessHistoryDays: (days) => {
    const { plan } = get();
    if (plan === 'pro') return true;
    return days <= 3;
  },
}), {
  name: 'oraculum-auth',
}));
