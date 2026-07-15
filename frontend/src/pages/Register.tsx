import { FormEvent, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { AlertCircle } from "lucide-react";
import { api, ApiError } from "@/api/client";
import { useAuthStore } from "@/store/auth";
import Button from "@/components/ui/Button";
import type { TokenResponse } from "@/api/types";

export default function Register() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const setToken = useAuthStore((s) => s.setToken);
  const navigate = useNavigate();

  async function submit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    if (password !== confirm) {
      setError("Passwords don't match");
      return;
    }
    setBusy(true);
    try {
      const data = await api.post<TokenResponse>("/auth/register", { email, password });
      setToken(data.access_token, email, data.is_onboarded);
      navigate("/onboarding");
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Registration failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div style={{ minHeight: "100vh", background: "var(--bg)" }}>
      <div className="card" style={{ maxWidth: 380, margin: "0 auto", marginTop: 80, padding: "36px 32px", boxShadow: "var(--shadow-lg)" }}>
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 10, marginBottom: 4 }}>
          <img
            src="/graduate-user-icon.png"
            alt=""
            style={{ width: 48, height: 48, objectFit: "contain", borderRadius: 12, background: "var(--surface)", border: "1px solid var(--border)", padding: 8 }}
          />
          <div className="text-16" style={{ fontWeight: 600, color: "var(--text-primary)" }}>
            PhD Copilot
          </div>
        </div>
        <div className="text-13 c-muted" style={{ textAlign: "center", marginBottom: 28 }}>
          Find PhD positions that fit you.
        </div>

        <form onSubmit={submit}>
          <div style={{ marginBottom: 12 }}>
            <label className="field-label">Email</label>
            <input type="email" className="input" value={email} onChange={(e) => setEmail(e.target.value)} required />
          </div>
          <div style={{ marginBottom: 12 }}>
            <label className="field-label">Password</label>
            <input
              type="password"
              className="input"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={8}
            />
          </div>
          <div>
            <label className="field-label">Confirm password</label>
            <input
              type="password"
              className="input"
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              required
              minLength={8}
            />
          </div>

          {error && (
            <div
              style={{
                marginTop: 16,
                background: "var(--danger-light)",
                border: "1px solid var(--danger-border)",
                borderRadius: 6,
                padding: "10px 12px",
                display: "flex",
                gap: 8,
                alignItems: "flex-start",
              }}
            >
              <AlertCircle size={14} className="c-danger" style={{ flexShrink: 0, marginTop: 1 }} />
              <span className="text-12 c-danger">{error}</span>
            </div>
          )}

          <Button type="submit" variant="primary" loading={busy} style={{ width: "100%", marginTop: 16 }}>
            Create account
          </Button>
        </form>

        <div className="text-12 c-faint" style={{ textAlign: "center", marginTop: 16 }}>
          Already have one?{" "}
          <Link to="/login" className="c-accent">
            Sign in
          </Link>
        </div>
      </div>
    </div>
  );
}
