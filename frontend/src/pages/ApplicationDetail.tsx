import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "@/api/client";
import type { ApplicationRead, DocsChecklistItem, RunResponse, Status } from "@/api/types";
import { KANBAN_COLUMNS } from "@/api/types";
import StatusBadge from "@/components/StatusBadge";
import DeadlineCountdown from "@/components/DeadlineCountdown";
import DocsChecklist from "@/components/DocsChecklist";
import JobProgressBar from "@/components/JobProgressBar";

export default function ApplicationDetail() {
  const { id } = useParams();
  const appId = Number(id);
  const qc = useQueryClient();
  const navigate = useNavigate();
  const [jobId, setJobId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  const { data, isLoading } = useQuery<ApplicationRead>({
    queryKey: ["application", appId],
    queryFn: () => api.get<ApplicationRead>(`/applications/${appId}`),
    enabled: !isNaN(appId),
  });

  const updateStatus = useMutation({
    mutationFn: (status: Status) => api.patch<ApplicationRead>(`/applications/${appId}`, { status }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["application", appId] });
      qc.invalidateQueries({ queryKey: ["applications"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
      setError(null);
    },
    onError: (e) => setError(e instanceof ApiError ? e.message : "Update failed"),
  });

  const updateDocs = useMutation({
    mutationFn: (items: DocsChecklistItem[]) =>
      api.patch<ApplicationRead>(`/applications/${appId}/docs`, { items }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["application", appId] }),
  });

  const draft = useMutation({
    mutationFn: () => api.post<RunResponse>(`/applications/${appId}/draft`),
    onSuccess: (r) => setJobId(r.job_id),
    onError: (e) => setError(e instanceof ApiError ? e.message : "Draft failed"),
  });

  const [notes, setNotes] = useState("");
  useEffect(() => {
    if (data) setNotes(data.notes ?? "");
  }, [data]);

  const saveNotes = useMutation({
    mutationFn: (text: string) =>
      api.patch<ApplicationRead>(`/applications/${appId}`, { notes: text }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["application", appId] }),
  });

  if (isLoading) return <p className="text-slate-500">Loading…</p>;
  if (!data) return null;

  return (
    <div className="grid md:grid-cols-[2fr_1fr] gap-6">
      <div className="space-y-4">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h1 className="text-2xl font-semibold">{data.listing.title}</h1>
            <p className="text-slate-600">{data.listing.institution} · {data.listing.country}</p>
            <div className="mt-2 flex items-center gap-3">
              <StatusBadge status={data.status} />
              <DeadlineCountdown deadline={data.deadline} />
            </div>
          </div>
          <Link className="btn-secondary" to={`/opportunities/${data.listing_id}`}>
            View listing
          </Link>
        </div>

        <div className="card space-y-3">
          <h3 className="font-medium">Change status</h3>
          <div className="flex flex-wrap gap-2">
            {KANBAN_COLUMNS.map((s) => (
              <button
                key={s}
                className={`btn ${s === data.status ? "btn-primary" : "btn-secondary"}`}
                disabled={updateStatus.isPending || s === data.status}
                onClick={() => updateStatus.mutate(s)}
              >
                {s}
              </button>
            ))}
          </div>
          {error && <p className="text-sm text-rose-600">{error}</p>}
          <p className="text-xs text-slate-500">
            Transitions are validated server-side (architecture section 10). You can't reach READY until every document is ticked.
          </p>
        </div>

        <div className="card space-y-3">
          <h3 className="font-medium">Cover letter</h3>
          {data.cover_letter_path ? (
            <p className="text-sm text-slate-600">
              Draft saved at <code className="text-xs">{data.cover_letter_path}</code>.
            </p>
          ) : (
            <p className="text-sm text-slate-500">No draft yet.</p>
          )}
          <div className="flex gap-2">
            <button
              className="btn-primary"
              disabled={draft.isPending}
              onClick={() => draft.mutate()}
            >
              {draft.isPending ? "Queuing…" : data.cover_letter_path ? "Regenerate draft" : "Generate draft"}
            </button>
            <button
              className="btn-secondary"
              onClick={() => navigate(`/tracker/${appId}/letter`)}
              disabled={!data.cover_letter_path}
            >
              Open editor
            </button>
          </div>
          <JobProgressBar
            jobId={jobId}
            label="Cover-letter generation"
            onDone={() => {
              qc.invalidateQueries({ queryKey: ["application", appId] });
              qc.invalidateQueries({ queryKey: ["applications"] });
            }}
          />
        </div>

        <div className="card space-y-2">
          <h3 className="font-medium">Notes</h3>
          <textarea
            className="input"
            rows={4}
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
          />
          <div className="flex justify-end">
            <button
              className="btn-secondary"
              onClick={() => saveNotes.mutate(notes)}
              disabled={saveNotes.isPending}
            >
              {saveNotes.isPending ? "Saving…" : "Save notes"}
            </button>
          </div>
        </div>
      </div>

      <aside className="space-y-4">
        <div className="card space-y-3">
          <h3 className="font-medium">Documents checklist</h3>
          <DocsChecklist
            items={(data.docs_checklist as DocsChecklistItem[]) || []}
            onChange={(items) => updateDocs.mutate(items)}
          />
          <p className="text-xs text-slate-500">
            All docs must be ticked before you can move to READY.
          </p>
        </div>

        <div className="card space-y-2 text-sm">
          <h3 className="font-medium">Application info</h3>
          <p><b>Priority:</b> {data.priority}</p>
          {data.next_action && <p><b>Next action:</b> {data.next_action}</p>}
          {data.applied_at && <p><b>Applied at:</b> {new Date(data.applied_at).toLocaleString()}</p>}
        </div>
      </aside>
    </div>
  );
}
