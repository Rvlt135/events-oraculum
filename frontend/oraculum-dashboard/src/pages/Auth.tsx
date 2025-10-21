import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { usePlanStore } from '../store/planStore';
import { Zap, Mail, Lock, CreditCard } from 'lucide-react';

export function Auth() {
  const [tab, setTab] = useState<'login' | 'register'>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const navigate = useNavigate();
  const { login } = usePlanStore();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    login(email, 'free');
    navigate('/');
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="text-center mb-8">
          <div className="inline-flex items-center gap-2 mb-4">
            <Zap className="h-10 w-10 text-blue-600" />
            <span className="text-3xl font-bold">Oraculum AI</span>
          </div>
          <p className="text-muted-foreground">
            AI-powered betting insights for sports events
          </p>
        </div>

        <div className="bg-white border rounded-lg shadow-lg overflow-hidden">
          <div className="flex border-b">
            <button
              onClick={() => setTab('login')}
              className={`flex-1 px-6 py-3 font-medium transition-colors ${
                tab === 'login'
                  ? 'bg-white border-b-2 border-blue-600 text-blue-600'
                  : 'bg-slate-50 text-muted-foreground hover:text-foreground'
              }`}
            >
              Login
            </button>
            <button
              onClick={() => setTab('register')}
              className={`flex-1 px-6 py-3 font-medium transition-colors ${
                tab === 'register'
                  ? 'bg-white border-b-2 border-blue-600 text-blue-600'
                  : 'bg-slate-50 text-muted-foreground hover:text-foreground'
              }`}
            >
              Register
            </button>
          </div>

          <form onSubmit={handleSubmit} className="p-6 space-y-4">
            <div>
              <label className="block text-sm font-medium mb-2">Email</label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="you@example.com"
                  required
                  className="w-full pl-10 pr-4 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-600"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-medium mb-2">Password</label>
              <div className="relative">
                <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-5 w-5 text-muted-foreground" />
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="••••••••"
                  required
                  className="w-full pl-10 pr-4 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-600"
                />
              </div>
            </div>

            <button
              type="submit"
              className="w-full bg-blue-600 text-white py-2 rounded-md font-medium hover:bg-blue-700 transition-colors"
            >
              {tab === 'login' ? 'Sign In' : 'Create Account'}
            </button>

            <div className="relative my-6">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t"></div>
              </div>
              <div className="relative flex justify-center text-sm">
                <span className="px-2 bg-white text-muted-foreground">или</span>
              </div>
            </div>

            <Link
              to="/pricing"
              className="flex items-center justify-center gap-2 w-full py-2 border rounded-md font-medium text-blue-600 border-blue-600 hover:bg-blue-50 transition-colors"
            >
              <CreditCard className="h-4 w-4" />
              Посмотреть тарифы
            </Link>
          </form>
        </div>

        <p className="text-center text-sm text-muted-foreground mt-4">
          {tab === 'login' ? (
            <>Нет аккаунта? <button onClick={() => setTab('register')} className="text-blue-600 hover:underline">Зарегистрируйтесь</button></>
          ) : (
            <>Уже есть аккаунт? <button onClick={() => setTab('login')} className="text-blue-600 hover:underline">Войдите</button></>
          )}
        </p>
      </div>
    </div>
  );
}
