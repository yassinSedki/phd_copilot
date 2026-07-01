import { useJobProgress } from "@/hooks/useJobProgress";

interface Props {
  jobId: number | null;
  onDone?: () => void;
  onFailed?: (err: string | null) => void;
  label?: string;
}

export default function JobProgressBar({ jobId, onDone, onFailed, label }: Props) {
  const { data } = useJobProgress(jobId);
  if (!jobId || !data) return null;

  if (data.status === "done") {
    onDone?.();
  } else if (data.status === "failed") {
    onFailed?.(data.error);
  }

  return (
    <div className="card">
      <div className="flex items-center justify-between text-sm">
        <div className="font-medium">{label ?? `Job #${data.id} (${data.type})`}</div>
        <div className="text-slate-500">{data.status}</div>
      </div>
      <div className="mt-2 h-2 bg-slate-100 rounded">
        <div
          className={`h-2 rounded ${data.status === "failed" ? "bg-rose-500" : "bg-brand-500"}`}
          style={{ width: `${data.status === "done" ? 100 : data.progress}%` }}
        />
      </div>
      {data.result_ref && data.status === "done" && (
        <p className="mt-2 text-xs text-slate-500">{data.result_ref}</p>
      )}
      {data.error && (
        <pre className="mt-2 text-xs text-rose-600 whitespace-pre-wrap">{data.error}</pre>
      )}
    </div>
  );
}
