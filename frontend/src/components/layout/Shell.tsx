import { useEffect } from "react";
import { Outlet, useLocation } from "react-router-dom";
import { useQueryClient } from "@tanstack/react-query";
import Sidebar from "./Sidebar";
import Topbar from "./Topbar";
import { useActiveJobStore } from "@/store/activeJob";
import { useJobProgress } from "@/hooks/useJobProgress";
import { api } from "@/api/client";

const TITLES: Record<string, string> = {
  "/dashboard": "Home",
  "/opportunities": "Opportunities",
  "/applications": "Applications",
  "/documents": "Documents",
  "/supervisors": "Supervisors",
  "/settings": "Settings",
};

function titleFor(pathname: string): string {
  for (const [prefix, title] of Object.entries(TITLES)) {
    if (pathname === prefix || pathname.startsWith(prefix + "/")) return title;
  }
  return "PhD Copilot";
}

export default function Shell() {
  const location = useLocation();
  const { job, setJob, setLastResult } = useActiveJobStore();
  const qc = useQueryClient();
  const { data: jobData } = useJobProgress(job?.jobId ?? null);

  useEffect(() => {
    if (job && jobData && ["done", "failed", "cancelled"].includes(jobData.status)) {
      // Snapshot the outcome BEFORE clearing the job — this is what the
      // dashboard shows the user so a search never ends silently.
      const meta = jobData.progress_meta ?? {};
      setLastResult({
        url: job.url,
        status: jobData.status as "done" | "failed" | "cancelled",
        found: meta.listings_found ?? 0,
        kept: meta.listings_kept_by_prefilter ?? 0,
        matched: meta.listings_matched ?? 0,
        duplicates: meta.duplicates_skipped ?? 0,
        pagesProcessed: meta.pages_processed ?? 0,
        stopReason: meta.stop_reason ?? null,
        droppedReasons: meta.dropped_by_prefilter ?? [],
        emptyReason: meta.empty_reason ?? null,
        error: jobData.error,
      });
      setJob(null);
      qc.invalidateQueries({ queryKey: ["dashboard"] });
      qc.invalidateQueries({ queryKey: ["listings"] });
      qc.invalidateQueries({ queryKey: ["applications"] });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [jobData?.status]);

  async function stopJob() {
    if (!job?.searchRunId) return;
    await api.post(`/search-runs/${job.searchRunId}/cancel`);
    setJob(null);
    qc.invalidateQueries({ queryKey: ["dashboard"] });
  }

  const meta = jobData?.progress_meta;
  const pageInfo = meta?.pages_processed
    ? `Page ${meta.pages_processed} · ${meta.listings_found ?? 0} found`
    : "Starting…";

  return (
    <div style={{ minHeight: "100vh", background: "var(--bg)" }}>
      <Sidebar
        activeJob={job && jobData && !["done", "failed", "cancelled"].includes(jobData.status) ? { ...job, pageInfo } : null}
        onStopJob={stopJob}
      />
      <Topbar title={titleFor(location.pathname)} />
      <main
        style={{
          marginLeft: 240,
          marginTop: 48,
          padding: "32px",
          maxWidth: 1200,
          minHeight: "calc(100vh - 48px)",
        }}
      >
        <Outlet />
      </main>
    </div>
  );
}
