import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import type { DashboardResponse } from "@/api/types";
import RunPipelineButton from "@/components/RunPipelineButton";
import ListingCard from "@/components/ListingCard";
import StatusBadge from "@/components/StatusBadge";
import DeadlineCountdown from "@/components/DeadlineCountdown";
import { KANBAN_COLUMNS } from "@/api/types";

export default function Dashboard() {
  const { data, isLoading } = useQuery<DashboardResponse>({
    queryKey: ["dashboard"],
    queryFn: () => api.get<DashboardResponse>("/dashboard"),
  });

  if (isLoading) return <p className="text-slate-500">Loading…</p>;
  if (!data) return null;

  return (
    <div className="space-y-6">
      <div className="flex items-end justify-between flex-wrap gap-3">
        <div>
          <h1 className="text-2xl font-semibold">Dashboard</h1>
          <p className="text-sm text-slate-500">
            {data.total_listings} listings · {data.total_applications} applications
            {data.last_run_at ? ` · last run ${new Date(data.last_run_at).toLocaleString()}` : ""}
          </p>
        </div>
        <RunPipelineButton />
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {KANBAN_COLUMNS.map((status) => (
          <div key={status} className="card">
            <div className="text-xs uppercase tracking-wide text-slate-500">{status}</div>
            <div className="text-2xl font-semibold mt-1">{data.counts_by_status[status] ?? 0}</div>
          </div>
        ))}
      </div>

      <section>
        <div className="flex items-center justify-between mb-3">
          <h2 className="font-semibold">Top matches</h2>
          <Link className="text-sm text-brand-600 hover:underline" to="/opportunities">
            View all →
          </Link>
        </div>
        {data.top_matches.length === 0 ? (
          <p className="text-sm text-slate-500">
            No scored listings yet. Click <b>Run pipeline</b> to ingest some.
          </p>
        ) : (
          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-3">
            {data.top_matches.map((l) => (
              <ListingCard key={l.id} listing={l} />
            ))}
          </div>
        )}
      </section>

      <div className="grid md:grid-cols-2 gap-6">
        <section>
          <h2 className="font-semibold mb-3">Action needed</h2>
          <ApplicationList apps={data.action_needed} empty="Nothing in DRAFTING or READY right now." />
        </section>
        <section>
          <h2 className="font-semibold mb-3">Upcoming deadlines</h2>
          <ApplicationList apps={data.upcoming_deadlines} empty="No deadlines in the next 21 days." />
        </section>
      </div>
    </div>
  );
}

function ApplicationList({
  apps,
  empty,
}: {
  apps: DashboardResponse["action_needed"];
  empty: string;
}) {
  if (apps.length === 0) {
    return <p className="text-sm text-slate-500">{empty}</p>;
  }
  return (
    <ul className="space-y-2">
      {apps.map((a) => (
        <li key={a.id}>
          <Link to={`/tracker/${a.id}`} className="card flex items-center justify-between hover:border-brand-500">
            <div className="min-w-0">
              <div className="font-medium truncate">{a.listing.title || "Untitled"}</div>
              <div className="text-xs text-slate-500 truncate">{a.listing.institution}</div>
            </div>
            <div className="flex items-center gap-3">
              <DeadlineCountdown deadline={a.deadline} />
              <StatusBadge status={a.status} />
            </div>
          </Link>
        </li>
      ))}
    </ul>
  );
}
