interface Props {
  flags: string[] | null | undefined;
}

export default function RedFlagList({ flags }: Props) {
  if (!flags || flags.length === 0) {
    return <p className="text-sm text-emerald-600">No red flags.</p>;
  }
  return (
    <ul className="space-y-1 text-sm text-rose-700">
      {flags.map((flag, i) => (
        <li key={i} className="flex gap-2">
          <span aria-hidden>!</span>
          <span>{flag}</span>
        </li>
      ))}
    </ul>
  );
}
