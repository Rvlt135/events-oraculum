import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { usePlanStore } from '../store/planStore';
import { authService } from '../services/authService';
import { Zap, Mail, Lock, CreditCard } from 'lucide-react';

export function Auth() {
  const [activeTab, setActiveTab] = useState<'email' | 'google'>('email');
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const { setAuth } = usePlanStore();

  const handleEmailSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    try {
      const response = mode === 'register'
        ? await authService.registerWithEmail(email, password)
        : await authService.loginWithEmail(email, password);

      setAuth(response.user, response.tokens.access_token, response.tokens.refresh_token);
      navigate('/');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Authentication failed');
    } finally {
      setLoading(false);
    }
  };

  const handleGoogleAuth = async () => {
    setLoading(true);
    setError('');

    try {
      if (import.meta.env.VITE_USE_MOCKS === 'true') {
        const mockCode = 'mock_google_code';
        const response = await authService.handleGoogleCallback(mockCode);
        setAuth(response.user, response.tokens.access_token, response.tokens.refresh_token);
        navigate('/');
      } else {
        window.location.href = authService.getGoogleAuthUrl();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Google authentication failed');
      setLoading(false);
    }
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
              onClick={() => setActiveTab('email')}
              className={`flex-1 px-6 py-3 font-medium transition-colors ${
                activeTab === 'email'
                  ? 'bg-white border-b-2 border-blue-600 text-blue-600'
                  : 'bg-slate-50 text-muted-foreground hover:text-foreground'
              }`}
            >
              Email
            </button>
            <button
              onClick={() => setActiveTab('google')}
              className={`flex-1 px-6 py-3 font-medium transition-colors ${
                activeTab === 'google'
                  ? 'bg-white border-b-2 border-blue-600 text-blue-600'
                  : 'bg-slate-50 text-muted-foreground hover:text-foreground'
              }`}
            >
              Google
            </button>
          </div>

          <div className="p-6">
            {error && (
              <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-md text-sm text-red-600">
                {error}
              </div>
            )}

            {activeTab === 'email' ? (
              <form onSubmit={handleEmailSubmit} className="space-y-4">
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
                      minLength={8}
                      className="w-full pl-10 pr-4 py-2 border rounded-md focus:outline-none focus:ring-2 focus:ring-blue-600"
                    />
                  </div>
                </div>

                <div className="flex gap-2">
                  <button
                    type="submit"
                    onClick={() => setMode('login')}
                    disabled={loading}
                    className="flex-1 bg-blue-600 text-white py-2 rounded-md font-medium hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {loading && mode === 'login' ? 'Loading...' : 'Sign In'}
                  </button>
                  <button
                    type="button"
                    onClick={(e) => {
                      setMode('register');
                      handleEmailSubmit(e as any);
                    }}
                    disabled={loading}
                    className="flex-1 bg-slate-100 text-slate-700 py-2 rounded-md font-medium hover:bg-slate-200 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {loading && mode === 'register' ? 'Loading...' : 'Create Account'}
                  </button>
                </div>

                <div className="text-center text-sm text-muted-foreground">
                  or <button type="button" onClick={() => setActiveTab('google')} className="text-blue-600 hover:underline">use Google</button>
                </div>
              </form>
            ) : (
              <div className="space-y-4">
                <button
                  onClick={handleGoogleAuth}
                  disabled={loading}
                  className="w-full flex items-center justify-center gap-3 bg-white border-2 border-slate-200 py-3 rounded-md font-medium hover:bg-slate-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <svg className="h-5 w-5" viewBox="0 0 24 24">
                    <path
                      fill="#4285F4"
                      d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                    />
                    <path
                      fill="#34A853"
                      d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                    />
                    <path
                      fill="#FBBC05"
                      d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                    />
                    <path
                      fill="#EA4335"
                      d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                    />
                  </svg>
                  {loading ? 'Loading...' : 'Continue with Google'}
                </button>

                <div className="text-center text-sm text-muted-foreground">
                  or <button type="button" onClick={() => setActiveTab('email')} className="text-blue-600 hover:underline">use email</button>
                </div>
              </div>
            )}

            <div className="relative my-6">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t"></div>
              </div>
              <div className="relative flex justify-center text-sm">
                <span className="px-2 bg-white text-muted-foreground">Need info?</span>
              </div>
            </div>

            <Link
              to="/pricing"
              className="flex items-center justify-center gap-2 w-full py-2 border rounded-md font-medium text-blue-600 border-blue-600 hover:bg-blue-50 transition-colors"
            >
              <CreditCard className="h-4 w-4" />
              View Pricing Plans
            </Link>
          </div>
        </div>

        <p className="text-center text-sm text-muted-foreground mt-4">
          By signing in, you agree to our Terms and Privacy Policy
        </p>
      </div>
    </div>
  );
}
