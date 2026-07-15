import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Bookmark, Trash2 } from "lucide-react";
import { api, ApiError } from "@/api/client";
import ScoreBadge from "@/components/ui/ScoreBadge";
import DeadlineText from "@/components/ui/DeadlineText";
import StatusTag from "@/components/ui/StatusTag";
import ConfirmDialog from "@/components/ui/ConfirmDialog";
import type { ListingRow } from "@/api/types";

function typeLabel(offer: string | null): string | null {
  if (!offer) return null;
  const t = offer.toLowerCase();
  if (t.includes("postdoc") || t.includes("post-doc")) return "Postdoc";
  if (t.includes("phd") || t.includes("doctoral")) return "PhD";
  return offer.length <= 12 ? offer : null;
}

export default function OpportunityRow({
  row,
  onOpen,
  onDeleteStart,
  onDeleteError,
}: {
  row: ListingRow;
  onOpen: () => void;
  /** Called the instant delete is confirmed, before the request even fires.
   * The parent excludes this id from the rendered list from then on,
   * regardless of what the ["listings"] cache does in between — the confirm
   * dialog's overlay is translucent, so a background refetch racing the
   * DELETE request (e.g. a window-focus refetch landing before the server
   * has committed it) would otherwise re-insert the row for a moment,
   * flashing disappear/reappear/disappear. */
  onDeleteStart: (id: number) => void;
  /** Called if the delete actually fails, so the parent un-hides the row. */
  onDeleteError: (id: number) => void;
}) {
  const qc = useQueryClient();
  const [confirmingDelete, setConfirmingDelete] = useState(false);

  const save = useMutation({
    mutationFn: () => api.post("/applications", { listing_id: row.id }),
    onSuccess: () => {
      // The new application must appear in the tracker and dashboard
      // counters, not just flip this row's bookmark.
      qc.invalidateQueries({ queryKey: ["listings"] });
      qc.invalidateQueries({ queryKey: ["applications"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
    },
    onError: (e) => {
      if (e instanceof ApiError && e.status === 409) qc.invalidateQueries({ queryKey: ["listings"] });
    },
  });

  const remove = useMutation({
    mutationFn: () => api.delete(`/listings/${row.id}`),
    // Optimistic removal: the row disappears the instant Delete is
    // confirmed instead of waiting for a second round-trip (the old
    // invalidateQueries-only approach refetched before the UI updated).
    onMutate: async () => {
      await qc.cancelQueries({ queryKey: ["listings"] });
      const previous = qc.getQueryData<ListingRow[]>(["listings"]);
      qc.setQueryData<ListingRow[]>(["listings"], (old) => old?.filter((l) => l.id !== row.id));
      return { previous };
    },
    onError: (_err, _vars, context) => {
      if (context?.previous) qc.setQueryData(["listings"], context.previous);
      onDeleteError(row.id);
    },
    onSettled: () => {
      // Deleting a listing cascades to its tracked application, so both
      // lists (and the dashboard counters) must eventually reconcile too.
      qc.invalidateQueries({ queryKey: ["listings"] });
      qc.invalidateQueries({ queryKey: ["applications"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });

  return (
    <>
      <tr onClick={onOpen}>
        <td>
          <ScoreBadge score={row.latest_score?.score} />
        </td>
        <td style={{ maxWidth: 280 }}>
          <div className="text-13 fw-500 c-primary truncate">{row.title || "Untitled"}</div>
          <div className="text-12 c-faint truncate">{row.institution}</div>
        </td>
        <td>{typeLabel(row.offer_type) && <span className="type-chip">{typeLabel(row.offer_type)}</span>}</td>
        <td>
          <span className="text-13 c-secondary">{row.country}</span>
        </td>
        <td>
          <DeadlineText deadline={row.deadline} dateOnly />
        </td>
        <td>{row.funding_type === "fully_funded" && <span className="funding-pill">Funded</span>}</td>
        <td>{row.status && <StatusTag status={row.status} />}</td>
        <td className="row-actions" onClick={(e) => e.stopPropagation()}>
          <div style={{ display: "flex", gap: 4 }}>
            <button
              className="btn-ghost"
              style={{ padding: 4 }}
              onClick={() => save.mutate()}
              title={row.application_id ? "Saved" : "Save to pipeline"}
              aria-label={row.application_id ? "Saved" : "Save to pipeline"}
            >
              <Bookmark size={16} className={row.application_id ? "c-accent" : "c-faint"} fill={row.application_id ? "currentColor" : "none"} />
            </button>
            <button
              className="btn-ghost"
              style={{ padding: 4 }}
              onClick={() => setConfirmingDelete(true)}
              title="Delete opportunity"
              aria-label="Delete opportunity"
            >
              <Trash2 size={16} className="c-faint" />
            </button>
          </div>
        </td>
      </tr>

      {confirmingDelete && (
        <ConfirmDialog
          title="Delete this opportunity?"
          message={
            row.application_id
              ? `"${row.title || "This listing"}" and its tracked application (checklist, notes, drafts) will be permanently removed. This can't be undone.`
              : `"${row.title || "This listing"}" will be permanently removed. This can't be undone.`
          }
          confirmLabel="Delete"
          loading={remove.isPending}
          onConfirm={() => {
            onDeleteStart(row.id);
            setConfirmingDelete(false);
            remove.mutate();
          }}
          onClose={() => setConfirmingDelete(false)}
        />
      )}
    </>
  );
}
