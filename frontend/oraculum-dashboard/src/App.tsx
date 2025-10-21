import { useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Header } from './components/Header';
import { ProtectedRoute } from './components/ProtectedRoute';
import { Dashboard } from './pages/Dashboard';
import { EventDetail } from './pages/EventDetail';
import { PredictedVsActual } from './pages/PredictedVsActual';
import { Auth } from './pages/Auth';
import { Pricing } from './pages/Pricing';
import { usePlanStore } from './store/planStore';

function App() {
  const { initializeAuth } = usePlanStore();

  useEffect(() => {
    if (import.meta.env.VITE_USE_MOCKS === 'true') {
      import('./mocks/browser').then(({ worker }) => {
        worker.start({
          onUnhandledRequest: 'bypass',
        });
      });
    }

    initializeAuth();
  }, [initializeAuth]);

  return (
    <BrowserRouter>
      <div className="min-h-screen bg-slate-50">
        <Routes>
          <Route path="/auth" element={<Auth />} />
          <Route path="/pricing" element={<Pricing />} />

          <Route
            path="/*"
            element={
              <>
                <Header />
                <Routes>
                  <Route path="/" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
                  <Route path="/event/:id" element={<ProtectedRoute><EventDetail /></ProtectedRoute>} />
                  <Route path="/history" element={<ProtectedRoute><PredictedVsActual /></ProtectedRoute>} />
                  <Route path="/history/:id" element={<ProtectedRoute><EventDetail /></ProtectedRoute>} />
                  <Route path="*" element={<Navigate to="/" replace />} />
                </Routes>
              </>
            }
          />
        </Routes>
      </div>
    </BrowserRouter>
  );
}

export default App;
