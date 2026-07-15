export default function CardHeader({ children }: { children: React.ReactNode }) {
  return (
    <div style={{ padding: "16px 20px", borderBottom: "1px solid var(--border)", display: "flex", alignItems: "center" }}>
      {children}
    </div>
  );
}
