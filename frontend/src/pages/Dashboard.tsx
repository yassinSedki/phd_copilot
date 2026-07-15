import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { Layers, Loader2, Send, Users } from "lucide-react";
import { api } from "@/api/client";
import type { ApplicationListResponse, DashboardResponse, ListingRow } from "@/api/types";
import SearchZone from "./dashboard/SearchZone";
import UrgentZone from "./dashboard/UrgentZone";
import FollowUpsZone from "./dashboard/FollowUpsZone";
import StatsRow from "./dashboard/StatsRow";

function greeting(): string {
  const h = new Date().getHours();
  if (h < 12) return "Good morning";
  if (h < 18) return "Good afternoon";
  return "Good evening";
}

/** Mirrors the real layout's shape so nothing jumps when data arrives —
 * same approach as Opportunities' table skeleton and Settings' page
 * skeleton, applied to the dashboard's header/search/stats shape. */
function DashboardSkeleton() {
  return (
    <div>
      <div style={{ margin: "8px 0 28px" }}>
        <div className="skeleton" style={{ width: 100, height: 11 }} />
        <div className="skeleton" style={{ width: 220, height: 28, marginTop: 10 }} />
        <div className="skeleton" style={{ width: 400, height: 14, marginTop: 12 }} />
      </div>
      <div className="card" style={{ padding: "20px 24px" }}>
        <div className="skeleton" style={{ width: 260, height: 22, marginBottom: 14 }} />
        <div className="skeleton" style={{ width: "100%", height: 40, borderRadius: 6 }} />
      </div>
      <div className="card" style={{ display: "flex", marginTop: 24, overflow: "hidden" }}>
        {[1, 2, 3, 4].map((i) => (
          <div key={i} style={{ flex: 1, padding: "16px 20px", borderLeft: i > 1 ? "1px solid var(--border)" : "none" }}>
            <div className="skeleton" style={{ width: 36, height: 26 }} />
            <div className="skeleton" style={{ width: 70, height: 10, marginTop: 8 }} />
          </div>
        ))}
      </div>
    </div>
  );
}

export default function Dashboard() {
  const { data, isLoading, isError } = useQuery<DashboardResponse>({
    queryKey: ["dashboard"],
    queryFn: () => api.get<DashboardResponse>("/dashboard"),
    staleTime: 30_000,
  });

  const { data: listings } = useQuery<ListingRow[]>({
    queryKey: ["listings", "dashboard-stats"],
    queryFn: () => api.get<ListingRow[]>("/listings?limit=200"),
  });

  const { data: appsAll } = useQuery<ApplicationListResponse>({
    queryKey: ["applications", "all", "dashboard-stats"],
    queryFn: () => api.get<ApplicationListResponse>("/applications?status=all&limit=500"),
  });

  if (isLoading) return <DashboardSkeleton />;
  if (isError || !data)
    return <p className="text-13 c-danger">The dashboard couldn't be loaded. Check that the backend is running, then refresh.</p>;

  const urgentDeadlines = data.urgent.filter((u) => u.kind === "deadline_near" || u.kind === "letter_ready_to_send");
  const followUps = data.urgent.filter((u) => u.kind === "reference_overdue" || u.kind === "reference_due_soon");

  const apps = appsAll?.items ?? [];
  const stats = [
    {
      label: "Opportunities",
      value: listings?.length ?? 0,
      to: "/opportunities",
      icon: Layers,
      accent: "var(--primary)",
    },
    {
      label: "In progress",
      value: apps.filter((a) => !["APPLIED", "REJECTED", "WITHDRAWN", "OFFER", "INTERVIEW"].includes(a.status)).length,
      to: "/applications",
      icon: Loader2,
      accent: "var(--warning)",
    },
    {
      label: "Applied",
      value: apps.filter((a) => a.status === "APPLIED").length,
      to: "/applications",
      icon: Send,
      accent: "var(--success)",
    },
    {
      label: "Interviews",
      value: apps.filter((a) => a.status === "INTERVIEW").length,
      to: "/applications",
      icon: Users,
      accent: "var(--violet)",
    },
  ];

  const isEmpty = urgentDeadlines.length === 0 && followUps.length === 0 && data.recent_searches.length === 0;

  return (
    <div>
      <div style={{ margin: "8px 0 28px" }}>
        <div className="uppercase-label c-faint">
          {new Date().toLocaleDateString(undefined, { weekday: "long", month: "long", day: "numeric" })}
        </div>
        <h1 className="display" style={{ fontSize: "2.25rem", marginTop: 6 }}>
          {greeting()}
        </h1>
        <p className="text-14 c-secondary" style={{ marginTop: 8, maxWidth: 560, lineHeight: 1.6 }}>
          Paste a listings URL below and the agent finds, filters, and scores positions against{" "}
          <Link to="/settings" className="c-accent">
            your profile and constraints
          </Link>
          .
        </p>
      </div>

      <SearchZone recentSearches={data.recent_searches} />

      <UrgentZone items={urgentDeadlines} />
      <FollowUpsZone items={followUps} />

      {isEmpty && (
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 10, padding: "48px 0" }}>
          <Layers size={40} className="c-faint" />
          <p className="text-13 c-muted" style={{ maxWidth: 380, textAlign: "center", lineHeight: 1.6 }}>
            Nothing here yet. Paste a listings URL above (a university job board, EURAXESS, a lab page). Matches land
            in <Link to="/opportunities" className="c-accent">Opportunities</Link>, and anything scoring above your
            threshold is tracked automatically in{" "}
            <Link to="/applications" className="c-accent">Applications</Link>.
          </p>
        </div>
      )}

      <StatsRow stats={stats} />
    </div>
  );
}
