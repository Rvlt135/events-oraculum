import { create } from 'zustand';

type PlanType = 'free' | 'pro';

interface PlanStore {
  plan: PlanType;
  setPlan: (plan: PlanType) => void;
  canAccessSport: (sport: string) => boolean;
  canAccessFullReasoning: () => boolean;
  canAccessFullVoting: () => boolean;
  canAccessHistoryDays: (days: number) => boolean;
}

export const usePlanStore = create<PlanStore>((set, get) => ({
  plan: 'free',

  setPlan: (plan) => set({ plan }),

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
}));
