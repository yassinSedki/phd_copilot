import { useEffect, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ExternalLink, Trash2 } from "lucide-react";
import { api } from "@/api/client";
import StatusDropdown from "@/components/ui/StatusDropdown";
import DeadlineText from "@/components/ui/DeadlineText";
import ConfirmDialog from "@/components/ui/ConfirmDialog";
import ChecklistItemRow, { OpenPane } from "./application/ChecklistItemRow";
import DocumentEditor from "./application/DocumentEditor";
import ReferenceRequestModal from "./application/ReferenceRequestModal";
import type { ApplicationListResponse, ApplicationRead, DocType, Status } from "@/api/types";

export default function ApplicationDetail() {
  const { id } = useParams();
  const appId = Number(id);
  const navigate = useNavigate();
  const qc = useQueryClient();
  const [pane, setPane] = useState<OpenPane | null>(null);
  const [notes, setNotes] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const [confirmingDelete, setConfirmingDelete] = useState(false);
  const [searchParams, setSearchParams] = useSearchParams();

  const { data, isLoading } = useQuery<ApplicationRead>({
    queryKey: ["application", appId],
    queryFn: () => api.get<ApplicationRead>(`/applications/${appId}`),
    enabled: !isNaN(appId),
  });

  useEffect(() => {
    const open = searchParams.get("open");
    if (open) {
      setPane({ kind: "document", itemId: open, docType: open });
      searchParams.delete("open");
      setSearchParams(searchParams, { replace: true });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const patchStatus = useMutation({
    mutationFn: (status: Status) => api.patch(`/applications/${appId}`, { status }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["application", appId] });
      qc.invalidateQueries({ queryKey: ["applications"] });
    },
  });

  const saveNotes = useMutation({
    mutationFn: (text: string) => api.patch(`/applications/${appId}`, { notes: text }),
    onSuccess: () => {
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
      // Keep the cached detail and the list's notes_preview in sync.
      qc.invalidateQueries({ queryKey: ["application", appId] });
      qc.invalidateQueries({ queryKey: ["applications"] });
    },
  });

  const regenerate = useMutation({
    mutationFn: () => api.post(`/applications/${appId}/checklist/regenerate`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["application", appId] }),
  });

  const remove = useMutation({
    mutationFn: () => api.delete(`/applications/${appId}`),
    onSuccess: () => {
      // Remove it from the cached list right away so navigating back to
      // /applications never shows it, even for an instant, before refetch.
      qc.setQueriesData<ApplicationListResponse>({ queryKey: ["applications"] }, (old) =>
        old ? { items: old.items.filter((r) => r.id !== appId), total: Math.max(0, old.total - 1) } : old
      );
      qc.invalidateQueries({ queryKey: ["applications"] });
      qc.invalidateQueries({ queryKey: ["listings"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
      navigate("/applications");
    },
  });

  if (isLoading || !data) {
    return (
      <div style={{ display: "flex", gap: 24, alignItems: "flex-start" }}>
        <div className="card" style={{ width: 340, flexShrink: 0, padding: 20 }}>
          <div className="skeleton" style={{ width: "80%", height: 18, marginBottom: 8 }} />
          <div className="skeleton" style={{ width: "50%", height: 12, marginBottom: 20 }} />
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12, marginBottom: 20 }}>
            <div className="skeleton" style={{ width: "70%", height: 24 }} />
            <div className="skeleton" style={{ width: "70%", height: 24 }} />
          </div>
          <div className="skeleton" style={{ width: "100%", height: 1, marginBottom: 16 }} />
          {[1, 2, 3].map((i) => (
            <div key={i} className="skeleton" style={{ width: "100%", height: 30, marginBottom: 8 }} />
          ))}
        </div>
        <div className="card" style={{ flex: 1, minHeight: 600, padding: 24 }}>
          <div className="skeleton" style={{ width: "40%", height: 18, marginBottom: 16 }} />
          <div className="skeleton" style={{ width: "100%", height: 200 }} />
        </div>
      </div>
    );
  }

  const items = data.docs_checklist ?? [];
  const readyCount = items.filter((i) => i.ready).length;
  const pct = items.length ? Math.round((readyCount / items.length) * 100) : 0;
  const allDone = items.length > 0 && readyCount === items.length;

  function closePane() {
    setPane(null);
    qc.invalidateQueries({ queryKey: ["application", appId] });
  }

  return (
    <div style={{ display: "flex", gap: 24, alignItems: "flex-start" }}>
      <div className="card" style={{ width: 340, flexShrink: 0, position: "sticky", top: 80, overflow: "hidden" }}>
        <div style={{ padding: 20 }}>
          <div className="text-16 fw-600 c-primary" style={{ marginBottom: 4 }}>
            {data.listing.title}
          </div>
          <div className="text-12 c-faint" style={{ marginBottom: 16 }}>
            {data.listing.institution}
          </div>

          {/* Supervisor/Score were hardcoded "—" here — the summary payload
              doesn't carry them, so they rendered as permanently-empty
              fields. Removed until the API exposes them. */}
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
            <div>
              <div className="text-10 c-faint uppercase-label">Deadline</div>
              <div style={{ marginTop: 2 }}>
                <DeadlineText deadline={data.deadline} />
              </div>
            </div>
            <div>
              <div className="text-10 c-faint uppercase-label">Status</div>
              <div style={{ marginTop: 2 }}>
                <StatusDropdown status={data.status} onChange={(s) => patchStatus.mutate(s)} />
              </div>
            </div>
          </div>

          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginTop: 12 }}>
            <Link to={`/opportunities`} className="text-12 c-accent" style={{ display: "inline-flex", alignItems: "center", gap: 4 }}>
              View original <ExternalLink size={12} />
            </Link>
            <button
              className="btn-ghost btn-ghost-sm"
              style={{ display: "inline-flex", alignItems: "center", gap: 4 }}
              onClick={() => setConfirmingDelete(true)}
            >
              <Trash2 size={13} className="c-faint" /> Delete
            </button>
          </div>
        </div>

        <hr className="divider" />

        <div style={{ padding: "16px 20px" }}>
          <div style={{ display: "flex", justifyContent: "space-between" }}>
            <span className="text-10 fw-600 c-faint uppercase-label">Application checklist</span>
            <span className="text-11 c-faint">
              {readyCount} of {items.length}
            </span>
          </div>
          <div style={{ height: 3, background: "var(--border)", borderRadius: 2, margin: "8px 0 12px" }}>
            <div
              style={{
                height: 3,
                borderRadius: 2,
                width: `${pct}%`,
                background: allDone ? "var(--success)" : "var(--accent)",
                transition: "width 300ms ease-out",
              }}
            />
          </div>
          {allDone && (
            <div className="text-12 c-success" style={{ marginBottom: 8 }}>
              ✓ Ready to apply
            </div>
          )}
          {items.length === 0 ? (
            <p className="text-13 c-muted">
              No checklist yet.{" "}
              <button className="text-13 c-accent" style={{ background: "none", border: "none", cursor: "pointer", padding: 0 }} onClick={() => regenerate.mutate()}>
                Generate
              </button>
            </p>
          ) : (
            items.map((item) => <ChecklistItemRow key={item.id} appId={appId} item={item} onOpenPane={setPane} />)
          )}
        </div>

        <hr className="divider" />

        <div style={{ padding: "16px 20px" }}>
          <div className="text-10 fw-600 c-faint uppercase-label" style={{ marginBottom: 8 }}>
            Notes
          </div>
          <textarea
            className="input tr"
            style={{ background: "var(--surface-sunken)", minHeight: 80, resize: "vertical" }}
            placeholder="Click to add notes about this application..."
            defaultValue={data.notes ?? ""}
            onChange={(e) => setNotes(e.target.value)}
            onBlur={() => notes !== null && saveNotes.mutate(notes)}
          />
          <div className="text-11 c-faint" style={{ opacity: saved ? 1 : 0, transition: "opacity 300ms" }}>
            Saved
          </div>
        </div>
      </div>

      <div className="card" style={{ flex: 1, minHeight: 600, display: "flex", flexDirection: "column" }}>
        {pane?.kind === "document" ? (
          <DocumentEditor appId={appId} docType={pane.docType as DocType} />
        ) : (
          <div style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 6, padding: 24 }}>
            <p className="text-13 fw-500 c-secondary">Select a document from the checklist to draft or edit it</p>
            <p className="text-12 c-faint" style={{ maxWidth: 360, textAlign: "center", lineHeight: 1.6 }}>
              Click "Generate" next to Cover letter, SOP, or Research proposal in the checklist on the left. The
              agent drafts it from your profile and this listing — you then refine it by chatting or editing
              directly, with full version history.
            </p>
          </div>
        )}
      </div>

      {pane?.kind === "reference" && <ReferenceRequestModal applicationId={appId} itemId={pane.itemId} onClose={closePane} />}

      {confirmingDelete && (
        <ConfirmDialog
          title="Delete this application?"
          message={`"${data.listing.title || "This application"}" will be removed from your tracker along with its checklist, notes, and drafts. The opportunity itself stays in your library and can be re-saved later. This can't be undone.`}
          confirmLabel="Delete"
          loading={remove.isPending}
          onConfirm={() => remove.mutate()}
          onClose={() => setConfirmingDelete(false)}
        />
      )}
    </div>
  );
}
