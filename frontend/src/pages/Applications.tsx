import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import ApplicationRow from "./application/ApplicationRow";
import type { ApplicationListResponse } from "@/api/types";

type SortField = "deadline" | "readiness" | "status" | "title";
type StatusFilter = "active" | "closed" | "all";

/** Same shimmering-bar pattern as Opportunities' table skeleton — the real
 * column layout is already visible while data loads, instead of a blank
 * gap or a plain "Loading…" line. */
function SkeletonRows() {
  const widths = [60, 220, 70, 90, 140, 20];
  return (
    <>
      {Array.from({ length: 6 }, (_, r) => (
        <tr key={r} style={{ cursor: "default" }}>
          {widths.map((w, c) => (
            <td key={c}>
              <span className="skeleton" style={{ width: w * (0.7 + ((r + c) % 3) * 0.15) }} />
            </td>
          ))}
        </tr>
      ))}
    </>
  );
}

export default function Applications() {
  const [sort, setSort] = useState<SortField>("deadline");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("active");

  const { data, isLoading } = useQuery<ApplicationListResponse>({
    queryKey: ["applications", sort, statusFilter],
    queryFn: () => api.get<ApplicationListResponse>(`/applications?sort=${sort}&status=${statusFilter}`),
  });

  return (
    <div>
      {/* "+ Add manually" was a dead button (no handler/endpoint) — removed. */}
      <h1 className="text-20 fw-600 c-primary">Applications</h1>
      <p className="text-13 c-muted" style={{ marginTop: 4, marginBottom: 24 }}>
        {data ? `${data.total} applications` : <span className="skeleton" style={{ width: 90 }} />}
      </p>

      <div style={{ display: "flex", gap: 8, marginBottom: 16 }}>
        {(["active", "closed", "all"] as StatusFilter[]).map((f) => (
          <button
            key={f}
            className={`btn btn-sm ${statusFilter === f ? "" : "btn-secondary"}`}
            style={statusFilter === f ? { background: "var(--ink)", color: "var(--surface)" } : undefined}
            onClick={() => setStatusFilter(f)}
          >
            {f[0].toUpperCase() + f.slice(1)}
          </button>
        ))}
        <select className="input" style={{ width: 160, marginLeft: "auto" }} value={sort} onChange={(e) => setSort(e.target.value as SortField)}>
          <option value="deadline">Sort: Deadline</option>
          <option value="readiness">Sort: Readiness</option>
          <option value="status">Sort: Status</option>
          <option value="title">Sort: Title</option>
        </select>
      </div>

      {!isLoading && (!data || data.items.length === 0) ? (
        <p className="text-13 c-muted">No applications yet. Save something from Opportunities.</p>
      ) : (
        <table className="data-table">
          <thead>
            <tr>
              <th style={{ width: 90 }}>Deadline</th>
              <th>Position</th>
              <th style={{ width: 100 }}>Docs ready</th>
              <th style={{ width: 130 }}>Status</th>
              <th>Notes</th>
              <th style={{ width: 40 }} />
            </tr>
          </thead>
          <tbody>
            {isLoading ? <SkeletonRows /> : data!.items.map((row) => <ApplicationRow key={row.id} row={row} />)}
          </tbody>
        </table>
      )}
    </div>
  );
}
