import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { ChevronRight } from "lucide-react";
import type { UrgencyItem } from "@/api/types";

const ACTION_LABEL: Record<string, string> = {
  reference_overdue: "Reference letter overdue",
  reference_due_soon: "Reference letter due soon",
};

export default function FollowUpsZone({ items }: { items: UrgencyItem[] }) {
  const [expanded, setExpanded] = useState(false);
  const navigate = useNavigate();
  if (items.length === 0) return null;

  const visible = expanded ? items : items.slice(0, 4);

  return (
    <div style={{ marginTop: 24 }}>
      <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between", marginBottom: 8 }}>
        <span className="text-11 fw-600 c-faint uppercase-label">Follow-ups</span>
        <Link to="/applications" className="text-12 c-accent">
          All applications →
        </Link>
      </div>
      {visible.map((item, i) => (
        <div
          key={`${item.kind}-${item.application_id}-${i}`}
          className="card card-hover tr"
          role="button"
          tabIndex={0}
          style={{
            padding: "14px 16px",
            marginBottom: 6,
            display: "flex",
            alignItems: "center",
            gap: 12,
            cursor: "pointer",
          }}
          onClick={() => navigate(item.cta.href)}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") {
              e.preventDefault();
              navigate(item.cta.href);
            }
          }}
        >
          <div style={{ flex: 1, minWidth: 0 }}>
            <div className="text-13 fw-500 c-primary truncate">{item.title}</div>
            <div className="text-12 c-faint truncate">
              {item.institution && <>{item.institution} · </>}
              <span className={item.kind === "reference_overdue" ? "c-danger" : "c-muted"}>
                {ACTION_LABEL[item.kind] ?? item.cta.label}
              </span>
            </div>
          </div>
          <ChevronRight size={14} className="c-faint" />
        </div>
      ))}
      {items.length > 4 && !expanded && (
        <button className="btn-ghost btn-ghost-sm" onClick={() => setExpanded(true)}>
          View all {items.length} →
        </button>
      )}
    </div>
  );
}
