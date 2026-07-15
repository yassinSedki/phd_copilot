import { FormEvent, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { BookOpen, Check, Filter, Gauge, Globe, Search, X } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { api } from "@/api/client";
import { useActiveJobStore } from "@/store/activeJob";
import { useJobProgress } from "@/hooks/useJobProgress";
import Button from "@/components/ui/Button";
import type { JobProgressMeta, RecentSearchItem, RunResponse } from "@/api/types";

function truncate(url: string, max = 40): string {
  return url.length > max ? url.slice(0, max) + "…" : url;
}

// Real, scrapable listing sources — one tap fills the search box with a
// working starting URL. Sources without a single canonical listings URL
// (LinkedIn, "university websites" in general) are deliberately left out
// rather than wired to a fake/non-functional chip.
const QUICK_SOURCES = [
  { label: "EURAXESS", url: "https://euraxess.ec.europa.eu/jobs/search" },
  { label: "AcademicJobsOnline", url: "https://academicjobsonline.org/ajo" },
  { label: "FindAPhD", url: "https://www.findaphd.com/phds/" },
];

/** Closure message for a run that finished WITHOUT pausing — always says
 * why there's nothing more, instead of just showing counts and going quiet. */
function stopReasonText(reason: string | null, pages: number): string | null {
  const pageWord = pages === 1 ? "page" : "pages";
  switch (reason) {
    case "exhausted":
      return `Checked all ${pages} ${pageWord} — no further pages were found. This source has been fully explored.`;
    case "loop_detected":
      return `Checked ${pages} ${pageWord} — the site started repeating listings I'd already seen, so I stopped there.`;
    case "no_results":
      return `Checked ${pages} ${pageWord} — the last one had no listings, so I stopped there.`;
    default:
      return null;
  }
}

type StepState = "done" | "active" | "pending";

interface AgentStep {
  icon: LucideIcon;
  label: string;
  detail: string | null;
  state: StepState;
}

/** Derive the agent's visible step timeline from the job's progress meta.
 * Long runs post meta sparsely — the timeline plus the elapsed clock and
 * shimmer keep the console visibly alive between updates. */
function deriveSteps(meta: JobProgressMeta | null | undefined): AgentStep[] {
  const found = meta?.listings_found;
  const kept = meta?.listings_kept_by_prefilter;
  const scoring = meta?.currently_checking;
  const matched = meta?.listings_matched;
  const dupes = meta?.duplicates_skipped;

  const readingDone = kept != null;
  const filteringDone = kept != null;
  const enrichActive = filteringDone && !scoring;
  const scoringActive = !!scoring;

  return [
    {
      icon: Globe,
      label: "Reading pages on the site",
      detail:
        meta?.pages_processed != null
          ? `page ${meta.pages_processed}${found != null ? ` · ${found} listings found` : ""}`
          : null,
      state: readingDone ? "done" : "active",
    },
    {
      icon: Filter,
      label: "Filtering against your profile & constraints",
      detail:
        kept != null && found != null
          ? `${kept} kept${found - kept > 0 ? ` · ${found - kept} filtered out` : ""}`
          : null,
      state: filteringDone ? "done" : readingDone ? "active" : "pending",
    },
    {
      icon: BookOpen,
      label: "Reading each kept listing's own page",
      detail: dupes ? `${dupes} already in your library, skipped` : null,
      state: scoringActive ? "done" : enrichActive ? "active" : "pending",
    },
    {
      icon: Gauge,
      label: "Scoring & tracking matches",
      detail: scoring
        ? `scoring "${truncate(scoring, 44)}"${matched != null ? ` · ${matched} matched so far` : ""}`
        : matched != null && matched > 0
          ? `${matched} matched so far`
          : null,
      state: scoringActive ? "active" : "pending",
    },
  ];
}

function StepIcon({ step }: { step: AgentStep }) {
  const Icon = step.icon;
  return (
    <span className={`agent-step-icon ${step.state}`}>
      {step.state === "done" ? (
        <Check size={11} strokeWidth={2.5} />
      ) : step.state === "active" ? (
        <span className="spinner" style={{ width: 10, height: 10, borderWidth: 1.5 }} />
      ) : (
        <Icon size={10} strokeWidth={2} />
      )}
    </span>
  );
}

/** mm:ss clock since the job was created — always ticking, so the user
 * never wonders whether a 5-minute search silently died. */
function useElapsed(createdAt: string | null | undefined): string {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(id);
  }, []);
  if (!createdAt) return "0:00";
  const secs = Math.max(0, Math.floor((now - new Date(createdAt).getTime()) / 1000));
  return `${Math.floor(secs / 60)}:${String(secs % 60).padStart(2, "0")}`;
}

export default function SearchZone({ recentSearches }: { recentSearches: RecentSearchItem[] }) {
  const [url, setUrl] = useState("");
  const { job, setJob, lastResult, setLastResult } = useActiveJobStore();
  const qc = useQueryClient();
  const { data: jobData } = useJobProgress(job?.jobId ?? null);

  const start = useMutation({
    mutationFn: (u: string) => api.post<RunResponse>("/runs/url", { url: u }),
    onSuccess: (data, u) => setJob({ jobId: data.job_id, searchRunId: data.search_run_id, url: u }),
  });

  const elapsed = useElapsed(jobData?.created_at);

  function submit(e: FormEvent) {
    e.preventDefault();
    if (!url.trim()) return;
    start.mutate(url.trim());
  }

  async function respond(action: "continue" | "cancel") {
    if (!job?.searchRunId) return;
    await api.post(`/search-runs/${job.searchRunId}/${action}`);
    qc.invalidateQueries({ queryKey: ["job", job.jobId] });
  }

  const isActive = !!job && jobData && !["done", "failed", "cancelled"].includes(jobData.status);
  const meta = jobData?.progress_meta;
  const steps = deriveSteps(meta);
  const activeStep = steps.find((s) => s.state === "active");

  return (
    <div className="card" style={{ padding: "20px 24px" }}>
      {isActive ? (
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <span className="pulse-dot" />
            <span className="text-13 fw-600 c-primary">Agent working</span>
            <span className="text-12 c-faint truncate" style={{ maxWidth: 300 }}>
              {truncate(job!.url, 36)}
            </span>
            <span className="data text-12 c-muted" style={{ marginLeft: "auto" }} title="Elapsed time">
              {elapsed}
            </span>
            <button className="btn-ghost btn-ghost-sm" onClick={() => respond("cancel")}>
              Stop
            </button>
          </div>

          {jobData?.status === "awaiting_continue" ? (
            <div
              className="surface-2"
              style={{ marginTop: 14, border: "1px solid var(--border)", borderRadius: 8, padding: "18px 20px", textAlign: "center" }}
            >
              <div className="text-14 fw-500 c-primary" style={{ marginBottom: 4 }}>
                {(meta?.checkpoint?.kept ?? meta?.listings_found ?? 0)} opportunities kept so far, across{" "}
                {meta?.pages_processed ?? meta?.checkpoint?.pages ?? "a few"} pages.
              </div>
              <div className="text-13 c-muted" style={{ marginBottom: 16 }}>
                {meta?.pause_reason === "page_limit"
                  ? "This source has more pages than a single run checks automatically — keep going?"
                  : "There are more pages beyond this batch — keep going?"}
              </div>
              <div style={{ display: "flex", justifyContent: "center", gap: 8 }}>
                <Button variant="primary" onClick={() => respond("continue")}>
                  Continue searching
                </Button>
                <Button variant="secondary" onClick={() => respond("cancel")}>
                  Stop and show results
                </Button>
              </div>
            </div>
          ) : (
            <>
              <div style={{ marginTop: 14 }}>
                {steps.map((s) => (
                  <div key={s.label} className="agent-step">
                    <StepIcon step={s} />
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div
                        className={
                          s.state === "active" ? "text-13 fw-500 shimmer-text" : "text-13 fw-500"
                        }
                        style={
                          s.state === "active"
                            ? undefined
                            : { color: s.state === "done" ? "var(--ink-secondary)" : "var(--ink-tertiary)" }
                        }
                      >
                        {s.label}
                      </div>
                      {s.detail && (
                        <div className="data text-11 c-faint" style={{ marginTop: 2 }}>
                          {s.detail}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>

              <div className="agent-progress" style={{ marginTop: 14 }}>
                <div className="agent-progress-fill" style={{ width: `${Math.max(4, jobData?.progress ?? 0)}%` }} />
              </div>

              <p className="text-12 c-faint" style={{ marginTop: 10, lineHeight: 1.5 }}>
                {activeStep?.label === "Scoring & tracking matches" || activeStep?.label === "Reading each kept listing's own page"
                  ? "This is the slow part — the agent visits every kept listing's own page and scores it against your full profile. A deep search can take a few minutes."
                  : "Deep searches take a few minutes. You can keep using the app — the search continues in the background."}
              </p>
            </>
          )}
        </div>
      ) : (
        <>
          <form onSubmit={submit}>
            <h2 className="display" style={{ fontSize: "1.5rem", marginBottom: 12 }}>
              Where are we looking today?
            </h2>
            <div style={{ display: "flex" }}>
              <input
                className="input tr"
                style={{ flex: 1, height: 40, fontSize: 14, borderRadius: "6px 0 0 6px" }}
                placeholder="Paste a listings URL: a university job board, EURAXESS, a lab page…"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
              />
              <Button
                type="submit"
                variant="primary"
                loading={start.isPending}
                style={{ height: 40, padding: "0 20px", borderRadius: "0 6px 6px 0" }}
              >
                <Search size={16} />
                Search
              </Button>
            </div>
          </form>

          {lastResult && (
            <div
              className="surface-2"
              style={{ marginTop: 16, border: "1px solid var(--border)", borderRadius: 8, padding: "14px 16px" }}
            >
              <div style={{ display: "flex", alignItems: "baseline", gap: 8 }}>
                <span className="text-13 fw-600 c-primary">
                  {lastResult.status === "done" ? "Search finished" : lastResult.status === "failed" ? "Search failed" : "Search stopped"}
                </span>
                <span className="text-11 c-faint truncate" style={{ flex: 1, minWidth: 0 }}>
                  {truncate(lastResult.url, 48)}
                </span>
                <button
                  className="btn-ghost"
                  style={{ padding: 2 }}
                  aria-label="Dismiss search summary"
                  onClick={() => setLastResult(null)}
                >
                  <X size={14} />
                </button>
              </div>

              <div style={{ marginTop: 10, display: "flex", gap: 20, flexWrap: "wrap" }}>
                {[
                  ["Found", lastResult.found],
                  ["Kept", lastResult.kept],
                  ...(lastResult.duplicates > 0 ? [["Duplicates", lastResult.duplicates] as const] : []),
                  ["Matched", lastResult.matched],
                ].map(([label, value]) => (
                  <div key={label}>
                    <div className="data text-20 c-primary" style={{ lineHeight: 1 }}>
                      {value}
                    </div>
                    <div className="uppercase-label c-faint" style={{ marginTop: 3 }}>
                      {label}
                    </div>
                  </div>
                ))}
              </div>

              {lastResult.status === "done" && !lastResult.emptyReason && stopReasonText(lastResult.stopReason, lastResult.pagesProcessed) && (
                <p className="text-12 c-secondary" style={{ marginTop: 8, lineHeight: 1.5 }}>
                  {stopReasonText(lastResult.stopReason, lastResult.pagesProcessed)}
                </p>
              )}
              {lastResult.emptyReason && (
                <p className="text-12 c-warning" style={{ marginTop: 8, lineHeight: 1.5 }}>
                  {lastResult.emptyReason}
                </p>
              )}
              {lastResult.error && (
                <p className="text-12 c-danger" style={{ marginTop: 8 }}>
                  {lastResult.error}
                </p>
              )}
              {lastResult.droppedReasons.length > 0 && (
                <div style={{ marginTop: 8 }}>
                  <div className="text-11 fw-500 c-faint uppercase-label" style={{ marginBottom: 4 }}>
                    Filtered out
                  </div>
                  {lastResult.droppedReasons.slice(0, 5).map((r, i) => (
                    <div key={i} className="text-12 c-muted" style={{ lineHeight: 1.6 }}>
                      · {r}
                    </div>
                  ))}
                  {lastResult.droppedReasons.length > 5 && (
                    <div className="text-11 c-faint">…and {lastResult.droppedReasons.length - 5} more</div>
                  )}
                </div>
              )}

              <div style={{ display: "flex", gap: 16, marginTop: 10 }}>
                {lastResult.kept > 0 && (
                  <Link to="/opportunities" className="text-12 c-accent">
                    View opportunities →
                  </Link>
                )}
                {lastResult.droppedReasons.length > 0 && (
                  <Link to="/settings" className="text-12 c-accent">
                    Adjust search constraints →
                  </Link>
                )}
              </div>
            </div>
          )}

          {recentSearches.length > 0 && (
            <div className="no-scrollbar" style={{ display: "flex", alignItems: "center", gap: 6, marginTop: 12, overflowX: "auto" }}>
              <span className="text-11 c-faint" style={{ marginRight: 2, flexShrink: 0 }}>
                Recent
              </span>
              {recentSearches.map((s) => (
                <span
                  key={s.id}
                  className="chip tr truncate"
                  style={{ maxWidth: 180, cursor: "pointer", flexShrink: 0 }}
                  title={s.url}
                  onClick={() => start.mutate(s.url)}
                >
                  {truncate(s.url, 30)}
                </span>
              ))}
            </div>
          )}

          <div className="no-scrollbar" style={{ display: "flex", alignItems: "center", gap: 6, marginTop: 8, overflowX: "auto" }}>
            <span className="text-11 c-faint" style={{ marginRight: 2, flexShrink: 0 }}>
              Quick sources
            </span>
            {QUICK_SOURCES.map((q) => (
              <span
                key={q.label}
                className="chip tr"
                style={{ cursor: "pointer", flexShrink: 0 }}
                title={q.url}
                onClick={() => setUrl(q.url)}
              >
                {q.label}
              </span>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
