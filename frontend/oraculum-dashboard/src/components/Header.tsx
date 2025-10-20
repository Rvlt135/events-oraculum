import { Link } from 'react-router-dom';
import { usePlanStore } from '../store/planStore';
import { Crown, Zap } from 'lucide-react';

export function Header() {
  const { plan, setPlan } = usePlanStore();

  return (
    <header className="border-b bg-white shadow-sm">
      <div className="container mx-auto px-4 py-4">
        <div className="flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2">
            <Zap className="h-6 w-6 text-primary" />
            <span className="text-xl font-bold">Oraculum AI</span>
          </Link>

          <nav className="flex items-center gap-6">
            <Link to="/" className="text-sm font-medium hover:text-primary transition-colors">
              Dashboard
            </Link>
            <Link to="/history" className="text-sm font-medium hover:text-primary transition-colors">
              History
            </Link>

            <div className="flex items-center gap-2 ml-4">
              <span className="text-sm text-muted-foreground">Plan:</span>
              <button
                onClick={() => setPlan(plan === 'free' ? 'pro' : 'free')}
                className={`flex items-center gap-1 px-3 py-1 rounded-full text-xs font-medium transition-colors ${
                  plan === 'pro'
                    ? 'bg-amber-100 text-amber-900 border border-amber-300'
                    : 'bg-secondary text-secondary-foreground'
                }`}
              >
                {plan === 'pro' && <Crown className="h-3 w-3" />}
                {plan === 'free' ? 'Free' : 'Pro'}
              </button>
            </div>
          </nav>
        </div>
      </div>
    </header>
  );
}
