import { ReactNode } from "react";

export default function Topbar({ title, actions }: { title: string; actions?: ReactNode }) {
  return (
    <header
      className="app-topbar"
      style={{
        position: "fixed",
        top: 0,
        left: 240,
        right: 0,
        height: 48,
        padding: "0 32px",
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        zIndex: 10,
      }}
    >
      <div className="text-14 fw-600 c-primary" style={{ letterSpacing: "-0.01em" }}>
        {title}
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>{actions}</div>
    </header>
  );
}
