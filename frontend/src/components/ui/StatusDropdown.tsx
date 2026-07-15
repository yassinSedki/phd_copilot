import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { Check, ChevronDown } from "lucide-react";
import { ALLOWED_TRANSITIONS, ALL_STATUSES, type Status } from "@/api/types";
import StatusTag, { STATUS_LABEL } from "./StatusTag";

export default function StatusDropdown({ status, onChange }: { status: Status; onChange: (s: Status) => void }) {
  const [open, setOpen] = useState(false);
  const [coords, setCoords] = useState<{ top: number; left: number } | null>(null);
  const triggerRef = useRef<HTMLButtonElement>(null);
  const menuRef = useRef<HTMLDivElement>(null);
  const allowed = new Set([status, ...ALLOWED_TRANSITIONS[status]]);

  // Rendered inside a <table> in most call sites — a plain position:absolute
  // dropdown gets clipped/painted-under by sibling <tr> rows regardless of
  // z-index (tables have their own stacking/painting quirks). A portal
  // positioned from the trigger's real screen coordinates sidesteps that
  // entirely — this is what made "Withdrawn" (the 4th option) look missing
  // when it was really just rendered underneath the next row.
  function openMenu() {
    const rect = triggerRef.current?.getBoundingClientRect();
    if (rect) setCoords({ top: rect.bottom + 4, left: rect.left });
    setOpen(true);
  }

  useEffect(() => {
    if (!open) return;
    function onClick(e: MouseEvent) {
      if (
        menuRef.current && !menuRef.current.contains(e.target as Node) &&
        triggerRef.current && !triggerRef.current.contains(e.target as Node)
      ) {
        setOpen(false);
      }
    }
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") setOpen(false);
    }
    function onScrollOrResize() {
      setOpen(false);
    }
    document.addEventListener("mousedown", onClick);
    document.addEventListener("keydown", onKey);
    window.addEventListener("scroll", onScrollOrResize, true);
    window.addEventListener("resize", onScrollOrResize);
    return () => {
      document.removeEventListener("mousedown", onClick);
      document.removeEventListener("keydown", onKey);
      window.removeEventListener("scroll", onScrollOrResize, true);
      window.removeEventListener("resize", onScrollOrResize);
    };
  }, [open]);

  return (
    <div style={{ position: "relative", display: "inline-block" }} onClick={(e) => e.stopPropagation()}>
      <button
        ref={triggerRef}
        className="tr"
        style={{ display: "flex", alignItems: "center", gap: 4, cursor: "pointer", background: "none", border: "none", padding: 0 }}
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={() => (open ? setOpen(false) : openMenu())}
      >
        <StatusTag status={status} />
        <ChevronDown size={12} className="c-faint" />
      </button>
      {open && coords &&
        createPortal(
          <div
            ref={menuRef}
            className="card"
            role="menu"
            style={{
              position: "fixed",
              top: coords.top,
              left: coords.left,
              minWidth: 160,
              padding: "4px 0",
              zIndex: 1000,
              boxShadow: "var(--shadow-float)",
            }}
          >
            {ALL_STATUSES.filter((s) => allowed.has(s)).map((s) => (
              <button
                key={s}
                role="menuitem"
                className="menu-item tr"
                onClick={() => {
                  setOpen(false);
                  if (s !== status) onChange(s);
                }}
              >
                <span style={{ width: 12 }}>{s === status && <Check size={12} className="c-accent" />}</span>
                {STATUS_LABEL[s]}
              </button>
            ))}
          </div>,
          document.body
        )}
    </div>
  );
}
