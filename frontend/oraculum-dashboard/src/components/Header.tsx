import { Link, useNavigate } from 'react-router-dom';
import { usePlanStore } from '../store/planStore';
import { Crown, Zap, LogOut } from 'lucide-react';

export function Header() {
  const { plan, isAuthenticated, logout } = usePlanStore();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/auth');
  };

  return (
    <header className="border-b bg-white shadow-sm">
      <div className="container mx-auto px-4 py-4">
        <div className="flex items-center justify-between">
          <Link to="/" className="flex items-center gap-2">
            <Zap className="h-6 w-6 text-primary" />
            <span className="text-xl font-bold">Oraculum AI</span>
          </Link>

          <nav className="flex items-center gap-6">
            {isAuthenticated && (
              <>
                <Link to="/" className="text-sm font-medium hover:text-primary transition-colors">
                  Dashboard
                </Link>
                <Link to="/history" className="text-sm font-medium hover:text-primary transition-colors">
                  History
                </Link>
              </>
            )}

            <Link to="/pricing" className="text-sm font-medium hover:text-primary transition-colors">
              Тарифы
            </Link>

            {isAuthenticated ? (
              <div className="flex items-center gap-4 ml-4 pl-4 border-l">
                <Link
                  to="/pricing"
                  className={`flex items-center gap-1 px-3 py-1 rounded-full text-xs font-medium transition-colors ${
                    plan === 'pro'
                      ? 'bg-amber-100 text-amber-900 border border-amber-300'
                      : 'bg-secondary text-secondary-foreground'
                  }`}
                >
                  {plan === 'pro' && <Crown className="h-3 w-3" />}
                  {plan === 'free' ? 'Free' : 'Pro'}
                </Link>
                <button
                  onClick={handleLogout}
                  className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground transition-colors"
                  title="Logout"
                >
                  <LogOut className="h-4 w-4" />
                </button>
              </div>
            ) : (
              <Link
                to="/auth"
                className="ml-4 px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700 transition-colors"
              >
                Войти
              </Link>
            )}
          </nav>
        </div>
      </div>
    </header>
  );
}
