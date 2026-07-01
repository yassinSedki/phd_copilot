import { DragEvent, useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "@/api/client";
import type { ApplicationRead, KanbanBoard, Status } from "@/api/types";
import { KANBAN_COLUMNS } from "@/api/types";
import StatusBadge from "@/components/StatusBadge";
import ScoreBadge from "@/components/ScoreBadge";
import DeadlineCountdown from "@/components/DeadlineCountdown";

export default function Tracker() {
  const qc = useQueryClient();
  const [dragErr, setDragErr] = useState<string | null>(null);

  const { data, isLoading } = useQuery<KanbanBoard>({
    queryKey: ["applications"],
    queryFn: () => api.get<KanbanBoard>("/applications"),
  });

  const mutation = useMutation({
    mutationFn: ({ id, status }: { id: number; status: Status }) =>
      api.patch<ApplicationRead>(`/applications/${id}`, { status }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["applications"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
    },
    onError: (e) =>
      setDragErr(e instanceof ApiError ? e.message : "Move failed"),
  });

  function onDrop(e: DragEvent, status: Status) {
    e.preventDefault();
    setDragErr(null);
    const id = Number(e.dataTransfer.getData("text/application-id"));
    if (id) mutation.mutate({ id, status });
  }

  if (isLoading) return <p className="text-slate-500">Loading…</p>;
  if (!data) return null;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Application tracker</h1>
        {dragErr && <span className="text-sm text-rose-600">{dragErr}</span>}
      </div>

      <div className="grid grid-flow-col auto-cols-[260px] gap-3 overflow-x-auto pb-3">
        {KANBAN_COLUMNS.map((status) => {
          const apps = data.columns[status] ?? [];
          return (
            <div
              key={status}
              className="bg-slate-100 rounded-lg p-2 flex flex-col gap-2 min-h-[300px]"
              onDragOver={(e) => e.preventDefault()}
              onDrop={(e) => onDrop(e, status)}
            >
              <div className="flex items-center justify-between px-1 py-1">
                <StatusBadge status={status} />
                <span className="text-xs text-slate-500">{apps.length}</span>
              </div>
              {apps.map((app) => (
                <ApplicationCard key={app.id} app={app} />
              ))}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function ApplicationCard({ app }: { app: ApplicationRead }) {
  return (
    <Link
      to={`/tracker/${app.id}`}
      draggable
      onDragStart={(e) => {
        e.dataTransfer.setData("text/application-id", String(app.id));
        e.dataTransfer.effectAllowed = "move";
      }}
      className="bg-white rounded-md border border-slate-200 p-3 shadow-sm hover:border-brand-500 block"
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="text-sm font-medium truncate">{app.listing.title || "Untitled"}</div>
          <div className="text-xs text-slate-500 truncate">{app.listing.institution}</div>
        </div>
        <ScoreBadge score={null} />
      </div>
      <div className="mt-2">
        <DeadlineCountdown deadline={app.deadline} />
      </div>
    </Link>
  );
}
