import { NavLink, useNavigate } from "react-router-dom";
import { LayoutDashboard, Layers, Briefcase, FileText, Users, Settings, LogOut } from "lucide-react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import { useAuthStore } from "@/store/auth";
import type { DashboardResponse } from "@/api/types";

const NAV_SECTIONS = [
  {
    label: "Workspace",
    items: [
      // Search lives as the hero zone on the dashboard — a /search route
      // never existed, so the old nav item silently redirected home.
      { to: "/dashboard", label: "Home", icon: LayoutDashboard },
      { to: "/documents", label: "Documents", icon: FileText },
    ],
  },
  {
    label: "Pipeline",
    items: [
      { to: "/opportunities", label: "Opportunities", icon: Layers },
      { to: "/applications", label: "Applications", icon: Briefcase, badgeKey: "applications" as const },
      { to: "/supervisors", label: "Supervisors", icon: Users },
    ],
  },
  {
    label: "",
    items: [{ to: "/settings", label: "Settings", icon: Settings }],
  },
];

interface ActiveJobInfo {
  jobId: number;
  url: string;
  pageInfo: string;
}

export default function Sidebar({ activeJob, onStopJob }: { activeJob?: ActiveJobInfo | null; onStopJob?: () => void }) {
  const { email, logout } = useAuthStore();
  const navigate = useNavigate();

  const { data } = useQuery<DashboardResponse>({
    queryKey: ["dashboard"],
    queryFn: () => api.get<DashboardResponse>("/dashboard"),
    staleTime: 30_000,
  });

  const urgentCount = data?.urgent.length ?? 0;

  return (
    <aside
      className="app-sidebar"
      style={{
        width: 240,
        position: "fixed",
        left: 0,
        top: 0,
        bottom: 0,
        display: "flex",
        flexDirection: "column",
      }}
    >
      <div style={{ padding: "16px 16px 6px", display: "flex", alignItems: "center", gap: 10 }}>
        <img src="/graduate-user-icon.png" alt="PhD Copilot" className="brand-mark" />
        <div style={{ minWidth: 0 }}>
          <div className="text-13 fw-600 c-primary" style={{ letterSpacing: "-0.01em" }}>
            PhD Copilot
          </div>
          <div className="text-11 c-faint truncate" style={{ marginTop: 1 }}>
            {email}
          </div>
        </div>
      </div>

      <nav style={{ padding: 8, flex: 1, overflowY: "auto" }}>
        {NAV_SECTIONS.map((section, si) => (
          <div key={si}>
            {section.label ? (
              <div className="sidebar-section">{section.label}</div>
            ) : (
              <hr className="divider" style={{ margin: "10px 2px" }} />
            )}
            {section.items.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) => `tr nav-item ${isActive ? "active" : ""}`}
                style={({ isActive }) => ({
                  display: "flex",
                  alignItems: "center",
                  height: 36,
                  padding: "0 10px",
                  borderRadius: 6,
                  marginBottom: 1,
                  fontSize: 13,
                  fontWeight: 500,
                  color: isActive ? "var(--primary)" : "var(--text-muted)",
                  background: isActive ? "var(--primary-soft)" : "transparent",
                  cursor: "pointer",
                })}
              >
                <item.icon size={16} strokeWidth={1.75} style={{ marginRight: 8, flexShrink: 0 }} />
                <span style={{ flex: 1 }}>{item.label}</span>
                {"badgeKey" in item && item.badgeKey === "applications" && urgentCount > 0 && (
                  <span
                    className="data"
                    style={{
                      fontSize: 10,
                      padding: "1px 6px",
                      borderRadius: 4,
                      background: "var(--danger-light)",
                      color: "var(--urgent)",
                    }}
                  >
                    {urgentCount}
                  </span>
                )}
              </NavLink>
            ))}
          </div>
        ))}
      </nav>

      {activeJob && (
        <div aria-live="polite" style={{ padding: "12px 16px", borderTop: "1px solid var(--border)" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 8 }}>
            <span className="uppercase-label c-faint" style={{ flex: 1 }}>
              Scraping
            </span>
            {onStopJob && (
              <button className="btn-ghost btn-ghost-sm" onClick={onStopJob}>
                Stop
              </button>
            )}
          </div>
          <div className="instrument-bar" />
          <div className="text-11 c-faint" style={{ marginTop: 6, display: "flex", justifyContent: "space-between", gap: 8 }}>
            <span className="truncate" style={{ maxWidth: 140 }}>
              {activeJob.url.replace(/^https?:\/\//, "")}
            </span>
            <span className="data" style={{ whiteSpace: "nowrap" }}>
              {activeJob.pageInfo}
            </span>
          </div>
        </div>
      )}

      <div style={{ padding: "12px 16px", borderTop: "1px solid var(--border)" }}>
        <button
          className="tr logout-row"
          style={{ display: "flex", alignItems: "center", gap: 8, cursor: "pointer", background: "none", border: "none", padding: 0 }}
          onClick={() => {
            logout();
            navigate("/login");
          }}
        >
          <LogOut size={14} strokeWidth={1.75} />
          <span className="text-12">Log out</span>
        </button>
      </div>
    </aside>
  );
}
