interface Props {
  score: number | null | undefined;
}

export default function ScoreBadge({ score }: Props) {
  if (score == null) {
    return <span className="pill bg-slate-100 text-slate-500">no score</span>;
  }
  const rounded = Math.round(score);
  const cls =
    rounded >= 80
      ? "bg-emerald-100 text-emerald-800"
      : rounded >= 65
      ? "bg-amber-100 text-amber-800"
      : rounded >= 40
      ? "bg-orange-100 text-orange-800"
      : "bg-rose-100 text-rose-800";
  return <span className={`pill ${cls}`}>{rounded}</span>;
}
