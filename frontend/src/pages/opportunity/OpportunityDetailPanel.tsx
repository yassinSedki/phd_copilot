import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ChevronDown, ExternalLink, FileText, Trash2, X } from "lucide-react";
import { api, ApiError } from "@/api/client";
import Button from "@/components/ui/Button";
import ScoreBadge from "@/components/ui/ScoreBadge";
import DeadlineText from "@/components/ui/DeadlineText";
import ConfirmDialog from "@/components/ui/ConfirmDialog";
import type { ApplicationRead, FitExplanation, ListingDetail, ListingRow } from "@/api/types";

/** Split, clean and dedupe the extracted required-docs list: one document
 * per row, stray bullets/periods stripped, first letter capitalized, and
 * "CV" vs "cv" style duplicates collapsed case-insensitively. */
function splitDocs(raw: string[] | null): string[] {
  if (!raw?.length) return [];
  const seen = new Set<string>();
  const out: string[] = [];
  for (const entry of raw.flatMap((d) => d.split(/[,;\n•·]/))) {
    let doc = entry.trim().replace(/^[-–—*\s]+/, "").replace(/[.\s]+$/, "");
    if (!doc) continue;
    doc = doc.charAt(0).toUpperCase() + doc.slice(1);
    const key = doc.toLowerCase();
    if (seen.has(key)) continue;
    seen.add(key);
    out.push(doc);
  }
  return out;
}

export default function OpportunityDetailPanel({
  listingId,
  onClose,
  onDeleteStart,
  onDeleteError,
}: {
  listingId: number;
  onClose: () => void;
  /** See OpportunityRow's onDeleteStart — the table row behind this panel
   * must hide the instant delete is confirmed, immune to any cache flicker
   * from a racing background refetch. */
  onDeleteStart: (id: number) => void;
  onDeleteError: (id: number) => void;
}) {
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [showBreakdown, setShowBreakdown] = useState(false);
  const [showFullDesc, setShowFullDesc] = useState(false);
  const [confirmingDelete, setConfirmingDelete] = useState(false);

  const { data, isLoading, isError } = useQuery<ListingDetail>({
    queryKey: ["listing", listingId],
    queryFn: () => api.get<ListingDetail>(`/listings/${listingId}`),
  });

  const fit = useQuery<FitExplanation>({
    queryKey: ["listing", listingId, "fit-explanation"],
    queryFn: () => api.get<FitExplanation>(`/listings/${listingId}/fit-explanation`),
    enabled: !!data?.latest_score,
    staleTime: Infinity,
  });

  const research = useMutation({
    mutationFn: () => api.post<ListingDetail>(`/listings/${listingId}/research`, {}),
    onSuccess: (updated) => {
      qc.setQueryData(["listing", listingId], updated);
      qc.invalidateQueries({ queryKey: ["listings"] });
    },
  });

  const save = useMutation({
    mutationFn: () => api.post<ApplicationRead>("/applications", { listing_id: listingId }),
    onSuccess: (app) => {
      qc.invalidateQueries({ queryKey: ["listings"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
      navigate(`/applications/${app.id}`);
    },
    onError: (e) => {
      if (e instanceof ApiError && e.status === 409) navigate("/applications");
    },
  });

  const remove = useMutation({
    mutationFn: () => api.delete(`/listings/${listingId}`),
    // Optimistic removal from the shared ["listings"] cache — the table
    // behind this panel updates instantly instead of waiting on a refetch.
    onMutate: async () => {
      await qc.cancelQueries({ queryKey: ["listings"] });
      const previous = qc.getQueryData<ListingRow[]>(["listings"]);
      qc.setQueryData<ListingRow[]>(["listings"], (old) => old?.filter((l) => l.id !== listingId));
      return { previous };
    },
    onError: (_err, _vars, context) => {
      if (context?.previous) qc.setQueryData(["listings"], context.previous);
      onDeleteError(listingId);
    },
    onSuccess: () => {
      onClose();
    },
    onSettled: () => {
      qc.invalidateQueries({ queryKey: ["listings"] });
      qc.invalidateQueries({ queryKey: ["applications"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });

  // Real loading/error states — this used to return null for both, which
  // rendered a silently blank panel.
  if (!data) {
    return (
      <div
        style={{
          position: "fixed",
          top: 48,
          right: 0,
          height: "calc(100vh - 48px)",
          width: 460,
          background: "var(--surface)",
          borderLeft: "1px solid var(--border)",
          boxShadow: "var(--shadow-float)",
          zIndex: 20,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          padding: 24,
        }}
      >
        {isLoading && <span className="text-13 c-muted">Loading listing…</span>}
        {isError && (
          <div style={{ textAlign: "center" }}>
            <p className="text-13 c-secondary" style={{ marginBottom: 12 }}>
              This listing couldn't be loaded.
            </p>
            <Button variant="secondary" size="sm" onClick={onClose}>
              Close
            </Button>
          </div>
        )}
      </div>
    );
  }
  const score = data.latest_score;
  const docs = splitDocs(data.required_docs);
  const description = data.description || "";
  const truncated = description.split("\n").slice(0, 3).join("\n");

  return (
    <div
      style={{
        position: "fixed",
        top: 48,
        right: 0,
        height: "calc(100vh - 48px)",
        width: 460,
        background: "var(--surface)",
        borderLeft: "1px solid var(--border)",
        boxShadow: "var(--shadow-float)",
        zIndex: 20,
        display: "flex",
        flexDirection: "column",
      }}
    >
      <div
        style={{
          height: 52,
          padding: "0 20px",
          borderBottom: "1px solid var(--border)",
          display: "flex",
          alignItems: "center",
        }}
      >
        <div style={{ flex: 1, minWidth: 0 }}>
          <div className="text-14 fw-600 c-primary truncate">{data.title}</div>
          <div className="text-12 c-faint truncate">{data.institution}</div>
        </div>
        <button
          className="btn-ghost"
          style={{ padding: 6 }}
          onClick={() => setConfirmingDelete(true)}
          title="Delete opportunity"
          aria-label="Delete opportunity"
        >
          <Trash2 size={16} />
        </button>
        <button className="btn-ghost" style={{ padding: 6 }} onClick={onClose} aria-label="Close">
          <X size={18} />
        </button>
        <Button variant="primary" size="sm" loading={save.isPending} onClick={() => save.mutate()} style={{ marginLeft: 8 }}>
          Save to pipeline
        </Button>
      </div>

      <div style={{ flex: 1, overflowY: "auto", padding: 20 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 16, marginBottom: 12 }}>
          <ScoreBadge score={score?.score} size={72} />
          <div>
            <div className="uppercase-label c-faint">Fit</div>
            <div className="data text-12 c-secondary" style={{ marginTop: 2 }}>
              {score ? `${Math.round(score.score)} / 100` : "not scored"}
            </div>
          </div>
        </div>

        {fit.data ? (
          <p className="text-14 c-secondary" style={{ lineHeight: 1.65 }}>
            {fit.data.paragraph}
          </p>
        ) : fit.isLoading ? (
          <p className="text-13 c-faint">Explaining the fit…</p>
        ) : (
          <p className="text-13 c-faint">No score yet.</p>
        )}

        <button
          className="text-12 c-faint"
          aria-expanded={showBreakdown}
          style={{ display: "flex", alignItems: "center", gap: 4, cursor: "pointer", marginTop: 8, background: "none", border: "none", padding: 0 }}
          onClick={() => setShowBreakdown((v) => !v)}
        >
          <ChevronDown size={14} style={{ transform: showBreakdown ? "rotate(180deg)" : undefined, transition: "transform 150ms" }} />
          Score breakdown
        </button>
        {showBreakdown && score?.fit_breakdown && (
          <div style={{ marginTop: 8, display: "flex", flexDirection: "column", gap: 8 }}>
            {Object.entries(score.fit_breakdown).map(([k, v]) => (
              <div key={k}>
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <span className="text-12 c-faint" style={{ textTransform: "capitalize" }}>
                    {k}
                  </span>
                  <span className="data text-12 c-secondary">{Math.round(v)}</span>
                </div>
                {/* calibration rule — hairline, ink, no color noise */}
                <div style={{ height: 2, background: "var(--border)", marginTop: 3 }}>
                  <div style={{ height: 2, background: "var(--ink-secondary)", width: `${Math.min(100, v)}%` }} />
                </div>
              </div>
            ))}
          </div>
        )}

        <hr className="divider" style={{ margin: "16px 0" }} />

        <div className="text-11 fw-500 c-faint uppercase-label" style={{ marginBottom: 8 }}>
          Supervisor
        </div>
        {data.supervisor_name && <div className="text-13 fw-500 c-secondary">{data.supervisor_name}</div>}
        {data.contact_email && (
          <a href={`mailto:${data.contact_email}`} className="text-13 c-accent" style={{ display: "block", marginTop: 2 }}>
            {data.contact_email}
          </a>
        )}
        <hr className="divider" style={{ margin: "16px 0" }} />

        <div className="text-11 fw-500 c-faint uppercase-label" style={{ marginBottom: 8 }}>
          Deadline
        </div>
        <div style={{ display: "flex", alignItems: "baseline", gap: 10 }}>
          <DeadlineText deadline={data.deadline} />
          {data.deadline && (
            <span className="text-13 c-secondary">
              {new Date(data.deadline).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" })}
            </span>
          )}
        </div>
        <hr className="divider" style={{ margin: "16px 0" }} />

        <div className="text-11 fw-500 c-faint uppercase-label" style={{ marginBottom: 8 }}>
          Documents needed to apply
        </div>
        {docs.length === 0 ? (
          <p className="text-13 c-faint italic">
            Not extracted yet. Use “Research this opportunity” below to read them from the opportunity's own page.
          </p>
        ) : (
          <ul
            style={{
              margin: 0,
              padding: 0,
              listStyle: "none",
              border: "1px solid var(--border)",
              borderRadius: 8,
              overflow: "hidden",
            }}
          >
            {docs.map((d, i) => (
              <li
                key={d}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 10,
                  padding: "8px 12px",
                  borderTop: i > 0 ? "1px solid var(--border)" : "none",
                  background: "var(--surface)",
                }}
              >
                <FileText size={14} style={{ color: "var(--caramel)", flexShrink: 0 }} />
                <span className="text-13 c-secondary">{d}</span>
              </li>
            ))}
          </ul>
        )}
        <hr className="divider" style={{ margin: "16px 0" }} />

        <div className="text-11 fw-500 c-faint uppercase-label" style={{ marginBottom: 8 }}>
          Description
        </div>
        <p className="text-13 c-secondary" style={{ lineHeight: 1.65, whiteSpace: "pre-wrap" }}>
          {showFullDesc ? description : truncated}
        </p>
        {description.length > truncated.length && (
          <span className="text-12 c-accent" style={{ cursor: "pointer" }} onClick={() => setShowFullDesc((v) => !v)}>
            {showFullDesc ? "Show less" : "Show more"}
          </span>
        )}
        <hr className="divider" style={{ margin: "16px 0" }} />
      </div>

      <div style={{ borderTop: "1px solid var(--border)" }}>
        {(data.url || data.application_url) && (
          <button
            className="btn-ghost"
            style={{ width: "100%", justifyContent: "flex-start", padding: "12px 20px" }}
            disabled={research.isPending}
            onClick={() => research.mutate()}
          >
            {research.isPending
              ? "Researching the listing page…"
              : research.isError
              ? "Research failed. Open the original listing below"
              : "Research this opportunity →"}
          </button>
        )}
        {data.application_url && data.application_url !== data.url && (
          <a
            href={data.application_url}
            target="_blank"
            rel="noreferrer"
            className="btn-ghost"
            style={{ width: "100%", justifyContent: "flex-start", padding: "12px 20px" }}
          >
            Apply here <ExternalLink size={14} style={{ marginLeft: "auto" }} />
          </a>
        )}
        {data.supervisor_name && (
          <button
            className="btn-ghost"
            style={{ width: "100%", justifyContent: "flex-start", padding: "12px 20px" }}
            onClick={() =>
              navigate(
                `/supervisors?professor=${encodeURIComponent(data.supervisor_name || "")}&institution=${encodeURIComponent(
                  data.institution || ""
                )}&topic=${encodeURIComponent(data.title || "")}`
              )
            }
          >
            Research this supervisor →
          </button>
        )}
        {data.url && (
          <a
            href={data.url}
            target="_blank"
            rel="noreferrer"
            className="btn-ghost"
            style={{ width: "100%", justifyContent: "flex-start", padding: "12px 20px" }}
          >
            View original listing <ExternalLink size={14} style={{ marginLeft: "auto" }} />
          </a>
        )}
      </div>

      {confirmingDelete && (
        <ConfirmDialog
          title="Delete this opportunity?"
          message={
            data.status
              ? `"${data.title || "This listing"}" and its tracked application (checklist, notes, drafts) will be permanently removed. This can't be undone.`
              : `"${data.title || "This listing"}" will be permanently removed. This can't be undone.`
          }
          confirmLabel="Delete"
          loading={remove.isPending}
          onConfirm={() => {
            onDeleteStart(listingId);
            setConfirmingDelete(false);
            remove.mutate();
          }}
          onClose={() => setConfirmingDelete(false)}
        />
      )}
    </div>
  );
}
