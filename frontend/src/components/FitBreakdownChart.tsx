interface Props {
  breakdown: Record<string, number> | null | undefined;
}

export default function FitBreakdownChart({ breakdown }: Props) {
  if (!breakdown) return <p className="text-sm text-slate-500">No fit breakdown.</p>;
  const entries = Object.entries(breakdown);
  return (
    <div className="space-y-2">
      {entries.map(([key, value]) => {
        const v = Math.max(0, Math.min(100, value));
        return (
          <div key={key}>
            <div className="flex justify-between text-xs text-slate-600">
              <span className="capitalize">{key}</span>
              <span>{Math.round(v)}</span>
            </div>
            <div className="h-2 bg-slate-100 rounded">
              <div
                className="h-2 rounded bg-brand-500"
                style={{ width: `${v}%` }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}
