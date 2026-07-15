import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { FileText, PenLine, FlaskConical, ArrowRight } from "lucide-react";
import { api } from "@/api/client";
import type { ApplicationListResponse, ApplicationRow, DocType } from "@/api/types";

const DOC_TYPES: { type: DocType; label: string; icon: typeof FileText; utility: string }[] = [
  {
    type: "cover_letter",
    label: "Cover letter",
    icon: FileText,
    utility: "A short, direct letter explaining why you're applying and why you fit — drafted from your profile and the listing, then refined by chatting with the agent.",
  },
  {
    type: "sop",
    label: "Statement of purpose",
    icon: PenLine,
    utility: "Your research background, motivation, and goals in your own academic voice — required by most PhD programmes as a standalone document.",
  },
  {
    type: "research_proposal",
    label: "Research proposal",
    icon: FlaskConical,
    utility: "A concrete proposed project (question, methods, timeline) — required where the programme expects you to arrive with your own research direction.",
  },
];

function statusFor(row: ApplicationRow, type: DocType): string | null {
  if (type === "cover_letter") return row.cover_letter_status;
  if (type === "sop") return row.sop_status;
  return null;
}

export default function Documents() {
  const { data, isLoading } = useQuery<ApplicationListResponse>({
    queryKey: ["applications", "all", "documents-page"],
    queryFn: () => api.get<ApplicationListResponse>("/applications?status=all&limit=200"),
  });
  const apps = data?.items ?? [];

  return (
    <div>
      <h1 className="text-20 fw-600 c-primary">Documents</h1>
      <p className="text-13 c-muted" style={{ marginTop: 4, marginBottom: 24, maxWidth: 620, lineHeight: 1.6 }}>
        Documents are drafted, refined, and versioned <strong>per application</strong> — a cover letter for one
        opportunity is a different document from the cover letter for another. There's no shared document library;
        instead, open an application below and use its editor.
      </p>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 14, marginBottom: 32 }}>
        {DOC_TYPES.map((d) => (
          <div key={d.type} className="card" style={{ padding: "18px 18px 16px" }}>
            <div
              style={{
                width: 32,
                height: 32,
                borderRadius: 8,
                background: "var(--primary-soft)",
                color: "var(--primary)",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                marginBottom: 12,
              }}
            >
              <d.icon size={16} />
            </div>
            <div className="text-14 fw-600 c-primary" style={{ marginBottom: 6 }}>
              {d.label}
            </div>
            <p className="text-12 c-muted" style={{ lineHeight: 1.55 }}>
              {d.utility}
            </p>
          </div>
        ))}
      </div>

      <div className="text-11 fw-600 c-faint uppercase-label" style={{ marginBottom: 8 }}>
        Open an application's editor
      </div>

      {isLoading ? (
        <div className="table-card">
          {[1, 2, 3].map((i) => (
            <div key={i} style={{ display: "flex", alignItems: "center", gap: 12, padding: "12px 16px", borderBottom: "1px solid var(--border)" }}>
              <div style={{ flex: 1 }}>
                <div className="skeleton" style={{ width: "40%", height: 14, marginBottom: 6 }} />
                <div className="skeleton" style={{ width: "25%", height: 11 }} />
              </div>
              <div className="skeleton" style={{ width: 220, height: 20 }} />
            </div>
          ))}
        </div>
      ) : apps.length === 0 ? (
        <p className="text-13 c-muted">
          No tracked applications yet. Save an opportunity from{" "}
          <Link to="/opportunities" className="c-accent">
            Opportunities
          </Link>{" "}
          to start drafting documents for it.
        </p>
      ) : (
        <div className="table-card">
          {apps.map((row) => (
            <div
              key={row.id}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 12,
                padding: "12px 16px",
                borderBottom: "1px solid var(--border)",
              }}
            >
              <div style={{ flex: 1, minWidth: 0 }}>
                <div className="text-13 fw-500 c-primary truncate">{row.title || "Untitled"}</div>
                <div className="text-11 c-faint truncate">{row.institution}</div>
              </div>
              {DOC_TYPES.map((d) => {
                const status = statusFor(row, d.type);
                return (
                  <Link
                    key={d.type}
                    to={`/applications/${row.id}?open=${d.type}`}
                    className="btn-ghost btn-ghost-sm tr"
                    style={{ display: "inline-flex", alignItems: "center", gap: 6 }}
                    title={`Open ${d.label} editor`}
                  >
                    <d.icon size={12} />
                    {d.label}
                    <span className="text-11 c-faint">{status ? `· ${status}` : "· not started"}</span>
                  </Link>
                );
              })}
              <Link to={`/applications/${row.id}`} className="btn-ghost btn-ghost-sm" aria-label="Open application">
                <ArrowRight size={14} />
              </Link>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
