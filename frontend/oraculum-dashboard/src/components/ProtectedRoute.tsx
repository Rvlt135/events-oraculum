import type { ReactNode } from 'react';
import { Navigate } from 'react-router-dom';
import { usePlanStore } from '../store/planStore';

interface ProtectedRouteProps {
  children: ReactNode;
}

export function ProtectedRoute({ children }: ProtectedRouteProps) {
  const { isAuthenticated } = usePlanStore();

  if (!isAuthenticated) {
    return <Navigate to="/auth" replace />;
  }

  return <>{children}</>;
}
