import { Navigate, Route, Routes } from "react-router-dom";

import Layout from "@/components/Layout";
import ProtectedRoute from "@/components/ProtectedRoute";
import Login from "@/pages/Login";
import Register from "@/pages/Register";
import OnboardingProfile from "@/pages/OnboardingProfile";
import Dashboard from "@/pages/Dashboard";
import Opportunities from "@/pages/Opportunities";
import OpportunityDetail from "@/pages/OpportunityDetail";
import Tracker from "@/pages/Tracker";
import ApplicationDetail from "@/pages/ApplicationDetail";
import LetterEditor from "@/pages/LetterEditor";
import DeepDive from "@/pages/DeepDive";
import Settings from "@/pages/Settings";

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />

      <Route element={<ProtectedRoute />}>
        <Route element={<Layout />}>
          <Route path="/onboarding/profile" element={<OnboardingProfile />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/opportunities" element={<Opportunities />} />
          <Route path="/opportunities/:id" element={<OpportunityDetail />} />
          <Route path="/tracker" element={<Tracker />} />
          <Route path="/tracker/:id" element={<ApplicationDetail />} />
          <Route path="/tracker/:id/letter" element={<LetterEditor />} />
          <Route path="/deepdive" element={<DeepDive />} />
          <Route path="/deepdive/:outreachId" element={<DeepDive />} />
          <Route path="/settings" element={<Settings />} />
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
        </Route>
      </Route>

      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}
