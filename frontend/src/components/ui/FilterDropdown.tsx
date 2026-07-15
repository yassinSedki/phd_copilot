import { ReactNode, useEffect, useRef, useState } from "react";
import { ChevronDown, ChevronUp } from "lucide-react";

export default function FilterDropdown({
  label,
  active,
  children,
}: {
  label: string;
  active: boolean;
  children: ReactNode;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function onClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  return (
    <div ref={ref} style={{ position: "relative" }}>
      <button
        className={`btn btn-sm tr ${active ? "" : "btn-secondary"}`}
        style={active ? { background: "var(--accent-light)", color: "var(--accent-text)", border: "1px solid var(--accent)" } : undefined}
        onClick={() => setOpen((v) => !v)}
      >
        {label}
        {open ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
      </button>
      {open && (
        <div
          className="card"
          style={{
            position: "absolute",
            top: "calc(100% + 4px)",
            left: 0,
            minWidth: 220,
            padding: 12,
            zIndex: 30,
            boxShadow: "var(--shadow-float)",
          }}
        >
          {children}
        </div>
      )}
    </div>
  );
}
