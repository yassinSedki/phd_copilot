import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Check } from "lucide-react";
import { api } from "@/api/client";
import type { ApplicationRead, DocsChecklistItem } from "@/api/types";

export type OpenPane = { kind: "document"; itemId: string; docType: string } | { kind: "reference"; itemId: string };

export default function ChecklistItemRow({
  appId,
  item,
  onOpenPane,
}: {
  appId: number;
  item: DocsChecklistItem;
  onOpenPane: (p: OpenPane) => void;
}) {
  const qc = useQueryClient();
  const patch = useMutation({
    mutationFn: (fields: Partial<DocsChecklistItem>) => api.patch<ApplicationRead>(`/applications/${appId}/docs/${item.id}`, fields),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["application", appId] });
      qc.invalidateQueries({ queryKey: ["applications"] });
    },
  });

  function action() {
    switch (item.kind) {
      case "document":
        return (
          <button className="btn btn-ghost btn-ghost-sm" onClick={() => onOpenPane({ kind: "document", itemId: item.id, docType: item.doc_type || "cover_letter" })}>
            {item.ready ? "Edit" : "Generate"}
          </button>
        );
      case "reference":
        return (
          <button className="btn btn-ghost btn-ghost-sm" onClick={() => onOpenPane({ kind: "reference", itemId: item.id })}>
            {item.reference_request_id ? "Requested" : "Send request"}
          </button>
        );
      case "portal":
        return (
          <button className="btn btn-ghost btn-ghost-sm" onClick={() => item.url && window.open(item.url, "_blank")}>
            Open portal ↗
          </button>
        );
      default:
        return (
          <button className="btn btn-ghost btn-ghost-sm" onClick={() => patch.mutate({ ready: !item.ready })}>
            {item.ready ? "Undo" : "Mark ready"}
          </button>
        );
    }
  }

  return (
    <div style={{ display: "flex", alignItems: "center", gap: 10, height: 44 }}>
      <button
        className={`checkbox tr ${item.ready ? "checked" : ""}`}
        onClick={() => patch.mutate({ ready: !item.ready })}
        disabled={patch.isPending}
      >
        {item.ready && <Check size={10} strokeWidth={3} />}
      </button>
      <div style={{ flex: 1 }}>
        <div className={`text-13 fw-500 ${item.ready ? "c-faint" : "c-secondary"}`} style={item.ready ? { textDecoration: "line-through" } : undefined}>
          {item.label}
        </div>
      </div>
      {action()}
    </div>
  );
}
