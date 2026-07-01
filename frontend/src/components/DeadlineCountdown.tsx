interface Props {
  deadline: string | null;
}

export default function DeadlineCountdown({ deadline }: Props) {
  if (!deadline) return <span className="text-slate-400 text-xs">no deadline</span>;
  const d = new Date(deadline);
  const now = new Date();
  const days = Math.ceil((d.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
  const fmt = d.toLocaleDateString();
  if (days < 0) return <span className="text-rose-600 text-xs font-medium">expired ({fmt})</span>;
  if (days <= 7) return <span className="text-rose-600 text-xs font-medium">in {days}d · {fmt}</span>;
  if (days <= 21) return <span className="text-amber-600 text-xs font-medium">in {days}d · {fmt}</span>;
  return <span className="text-slate-500 text-xs">in {days}d · {fmt}</span>;
}
