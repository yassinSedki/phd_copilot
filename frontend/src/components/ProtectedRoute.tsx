import { Navigate, Outlet, useLocation } from "react-router-dom";
import { useAuthStore } from "@/store/auth";

const ONBOARDING_PATH = "/onboarding";

export default function ProtectedRoute({ requireOnboarded = true }: { requireOnboarded?: boolean }) {
  const token = useAuthStore((s) => s.token);
  const isOnboarded = useAuthStore((s) => s.isOnboarded);
  const location = useLocation();

  if (!token) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }
  if (requireOnboarded && !isOnboarded && location.pathname !== ONBOARDING_PATH) {
    return <Navigate to={ONBOARDING_PATH} replace />;
  }
  if (!requireOnboarded && isOnboarded && location.pathname === ONBOARDING_PATH) {
    return <Navigate to="/dashboard" replace />;
  }
  return <Outlet />;
}
