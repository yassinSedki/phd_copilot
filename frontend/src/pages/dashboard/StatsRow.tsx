import { Link } from "react-router-dom";
import type { LucideIcon } from "lucide-react";

interface Stat {
  label: string;
  value: number;
  icon: LucideIcon;
  accent: string;
  /** Where clicking the card takes the user — every stat is a doorway. */
  to?: string;
}

/** A single instrument strip — mono numbers do the talking, hairline
 * dividers separate the cells instead of four competing card borders. */
export default function StatsRow({ stats }: { stats: Stat[] }) {
  return (
    <div className="card" style={{ display: "flex", marginTop: 24, overflow: "hidden" }}>
      {stats.map((s, i) => {
        const body = (
          <>
            <div className="data" style={{ fontSize: 26, color: "var(--ink)", lineHeight: 1 }}>
              {s.value}
            </div>
            <div className="uppercase-label c-faint" style={{ marginTop: 6, display: "flex", alignItems: "center", gap: 5 }}>
              <s.icon size={11} style={{ color: s.accent, flexShrink: 0 }} />
              {s.label}
            </div>
          </>
        );
        const className = `tr ${s.to ? "card-hover" : ""}`;
        const style: React.CSSProperties = {
          flex: 1,
          padding: "16px 20px",
          display: "block",
          borderLeft: i > 0 ? "1px solid var(--border)" : "none",
        };
        return s.to ? (
          <Link key={s.label} to={s.to} className={className} style={style} title={`Open ${s.label.toLowerCase()}`}>
            {body}
          </Link>
        ) : (
          <div key={s.label} className={className} style={style}>
            {body}
          </div>
        );
      })}
    </div>
  );
}
