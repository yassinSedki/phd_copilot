import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Trash2 } from "lucide-react";
import { api } from "@/api/client";
import DeadlineText from "@/components/ui/DeadlineText";
import StatusDropdown from "@/components/ui/StatusDropdown";
import ConfirmDialog from "@/components/ui/ConfirmDialog";
import type { ApplicationListResponse, ApplicationRow as Row, Status } from "@/api/types";

const CLOSED: Status[] = ["APPLIED", "REJECTED", "WITHDRAWN", "OFFER"];

export default function ApplicationRow({ row }: { row: Row }) {
  const [confirmingDelete, setConfirmingDelete] = useState(false);
  // Survives cache flicker: a background refetch racing the DELETE request
  // (e.g. window-focus refetch landing before the server commits the
  // delete) can briefly re-insert this row into the cache, flashing
  // disappear/reappear/disappear through the confirm dialog's translucent
  // overlay. Once confirmed, this row hides itself permanently regardless.
  const [hidden, setHidden] = useState(false);
  const navigate = useNavigate();
  const qc = useQueryClient();

  const patchStatus = useMutation({
    mutationFn: (status: Status) => api.patch(`/applications/${row.id}`, { status }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["applications"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });

  const remove = useMutation({
    mutationFn: () => api.delete(`/applications/${row.id}`),
    // Optimistic removal: the row disappears instantly instead of waiting
    // for a refetch. The list is cached per (sort, statusFilter) combo, so
    // setQueriesData (partial key match) updates every cached variant at once.
    onMutate: async () => {
      await qc.cancelQueries({ queryKey: ["applications"] });
      const previous = qc.getQueriesData<ApplicationListResponse>({ queryKey: ["applications"] });
      qc.setQueriesData<ApplicationListResponse>({ queryKey: ["applications"] }, (old) =>
        old ? { items: old.items.filter((r) => r.id !== row.id), total: Math.max(0, old.total - 1) } : old
      );
      return { previous };
    },
    onError: (_err, _vars, context) => {
      setHidden(false);
      context?.previous?.forEach(([key, data]) => qc.setQueryData(key, data));
    },
    onSettled: () => {
      // The underlying listing stays put — only tracking (checklist, notes,
      // drafts, reference requests) is removed. It can be re-saved from
      // Opportunities at any time.
      qc.invalidateQueries({ queryKey: ["applications"] });
      qc.invalidateQueries({ queryKey: ["listings"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });

  if (hidden) return null;

  const closed = CLOSED.includes(row.status) && row.status !== "OFFER";

  return (
    <>
      <tr style={{ opacity: closed ? 0.5 : 1 }} onClick={() => navigate(`/applications/${row.id}`)}>
        <td style={{ width: 90 }}>
          {closed ? (
            <span className="text-11 c-faint">{row.status === "APPLIED" ? "Applied" : "Closed"}</span>
          ) : (
            <DeadlineText deadline={row.deadline} dateOnly />
          )}
        </td>
        <td>
          <div className="text-13 fw-500 c-primary truncate">{row.title || "Untitled"}</div>
          <div className="text-12 c-faint truncate">{row.institution}</div>
        </td>
        <td style={{ width: 100 }}>
          <div style={{ display: "flex", gap: 3 }}>
            {Array.from({ length: 5 }).map((_, i) => (
              <span
                key={i}
                style={{
                  width: 7,
                  height: 7,
                  borderRadius: "50%",
                  background: i < Math.round((row.readiness_score / 100) * 5) ? "var(--accent)" : "var(--border-strong)",
                }}
              />
            ))}
          </div>
          <div className="data text-11 c-faint" style={{ marginTop: 2 }}>
            {Math.round((row.readiness_score / 100) * 5)}/5
          </div>
        </td>
        <td style={{ width: 130 }} onClick={(e) => e.stopPropagation()}>
          <StatusDropdown status={row.status} onChange={(s) => patchStatus.mutate(s)} />
        </td>
        <td>
          <span className={`text-12 c-faint truncate ${row.notes_preview ? "" : "italic"}`} style={{ display: "block", maxWidth: 200 }}>
            {row.notes_preview ? row.notes_preview.slice(0, 40) : "No notes"}
          </span>
        </td>
        <td className="row-actions" onClick={(e) => e.stopPropagation()}>
          <button
            className="btn-ghost"
            style={{ padding: 4 }}
            onClick={() => setConfirmingDelete(true)}
            title="Delete application"
            aria-label="Delete application"
          >
            <Trash2 size={16} className="c-faint" />
          </button>
        </td>
      </tr>

      {confirmingDelete && (
        <ConfirmDialog
          title="Delete this application?"
          message={`"${row.title || "This application"}" will be removed from your tracker along with its checklist, notes, and drafts. The opportunity itself stays in your library and can be re-saved later. This can't be undone.`}
          confirmLabel="Delete"
          loading={remove.isPending}
          onConfirm={() => {
            setHidden(true);
            setConfirmingDelete(false);
            remove.mutate();
          }}
          onClose={() => setConfirmingDelete(false)}
        />
      )}
    </>
  );
}
