import type { DocsChecklistItem } from "@/api/types";

interface Props {
  items: DocsChecklistItem[];
  onChange: (items: DocsChecklistItem[]) => void;
  disabled?: boolean;
}

export default function DocsChecklist({ items, onChange, disabled }: Props) {
  const toggle = (idx: number) => {
    if (disabled) return;
    const next = items.map((item, i) => (i === idx ? { ...item, ready: !item.ready } : item));
    onChange(next);
  };

  if (items.length === 0) {
    return <p className="text-sm text-slate-500">No required documents listed.</p>;
  }
  return (
    <ul className="space-y-2">
      {items.map((item, i) => (
        <li key={i} className="flex items-center gap-2">
          <input
            type="checkbox"
            checked={item.ready}
            onChange={() => toggle(i)}
            disabled={disabled}
            className="h-4 w-4 rounded border-slate-300"
          />
          <span className={item.ready ? "text-slate-700" : "text-slate-500"}>{item.doc}</span>
        </li>
      ))}
    </ul>
  );
}
