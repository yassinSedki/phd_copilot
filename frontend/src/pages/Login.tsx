import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api, ApiError } from "@/api/client";
import { useAuthStore } from "@/store/auth";
import type { TokenResponse } from "@/api/types";

export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const setToken = useAuthStore((s) => s.setToken);
  const navigate = useNavigate();

  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const data = await api.post<TokenResponse>("/auth/login", { email, password });
      setToken(data.access_token, email);
      navigate("/dashboard");
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Login failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="min-h-screen grid place-items-center px-6">
      <form onSubmit={submit} className="card w-full max-w-sm space-y-4">
        <h1 className="text-xl font-semibold text-brand-700">phd-copilot</h1>
        <p className="text-sm text-slate-500">Sign in to continue.</p>
        <div>
          <label className="label">Email</label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="input"
            required
          />
        </div>
        <div>
          <label className="label">Password</label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="input"
            required
            minLength={8}
          />
        </div>
        {error && <p className="text-sm text-rose-600">{error}</p>}
        <button type="submit" className="btn-primary w-full" disabled={busy}>
          {busy ? "Signing in…" : "Sign in"}
        </button>
        <p className="text-sm text-slate-500">
          No account?{" "}
          <Link to="/register" className="text-brand-600 hover:underline">
            Create one
          </Link>
        </p>
      </form>
    </div>
  );
}
