import { DragEvent, useState } from "react";
import { Upload, FileText, X, CheckCircle } from "lucide-react";
import { api, ApiError } from "@/api/client";
import Button from "@/components/ui/Button";
import type { ExtractedProfile } from "@/api/types";

const LOG_LINES = [
  "Reading your PDF",
  "Extracting text and structure",
  "Spotting education and degrees",
  "Identifying research areas",
  "Collecting methods and tools",
  "Scanning for publications",
  "Picking up languages and locations",
  "Building your profile",
];
// Seconds between line advances — the last line keeps pulsing until the
// server actually answers, so the panel never looks stalled.
const LINE_INTERVAL_MS = 2200;

const EMPTY_PROFILE: ExtractedProfile = {
  full_name: null,
  email: null,
  phone: null,
  research_summary: null,
  research_areas: [],
  methods: [],
  programming_languages: [],
  degree_subject: null,
  graduation_year: null,
  career_stage: null,
  languages_spoken: [],
  publications: [],
  geographic_hints: [],
};

export default function StepUploadCv({ onDone }: { onDone: (extracted: ExtractedProfile | null) => void }) {
  const [file, setFile] = useState<File | null>(null);
  const [dragOver, setDragOver] = useState(false);
  const [processing, setProcessing] = useState(false);
  const [visibleLines, setVisibleLines] = useState(0);
  const [error, setError] = useState<string | null>(null);

  function pickFile(f: File) {
    if (!f.name.toLowerCase().endsWith(".pdf")) {
      setError("Please upload a PDF.");
      return;
    }
    setError(null);
    setFile(f);
  }

  const [done, setDone] = useState(false);

  async function submit() {
    if (!file) return;
    setProcessing(true);
    setError(null);
    setVisibleLines(1);

    // Advance one line at a time but never past the last: it stays "in
    // progress" until the request actually resolves.
    const ticker = setInterval(
      () => setVisibleLines((n) => Math.min(n + 1, LOG_LINES.length)),
      LINE_INTERVAL_MS
    );

    try {
      const form = new FormData();
      form.append("file", file);
      const extracted = await api.postForm<ExtractedProfile>("/onboarding/cv", form);
      clearInterval(ticker);
      setVisibleLines(LOG_LINES.length);
      setDone(true);
      setTimeout(() => onDone(extracted), 700);
    } catch (e) {
      clearInterval(ticker);
      setProcessing(false);
      setVisibleLines(0);
      setError(e instanceof ApiError ? e.message : "Could not read that CV.");
    }
  }

  return (
    <div>
      <h1 className="text-20 fw-600 c-primary" style={{ marginBottom: 8 }}>
        Upload your CV
      </h1>
      <p className="text-13 c-muted" style={{ marginBottom: 24 }}>
        We'll read it and pre-fill your profile. Takes about 20 seconds.
      </p>

      {!processing ? (
        <label
          onDragOver={(e: DragEvent) => {
            e.preventDefault();
            setDragOver(true);
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={(e: DragEvent) => {
            e.preventDefault();
            setDragOver(false);
            const f = e.dataTransfer.files?.[0];
            if (f) pickFile(f);
          }}
          className="tr"
          style={{
            height: 148,
            border: `2px dashed ${dragOver ? "var(--accent)" : "var(--border-strong)"}`,
            borderRadius: 8,
            background: dragOver ? "var(--accent-light)" : "var(--surface)",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            gap: 8,
            cursor: "pointer",
            position: "relative",
          }}
        >
          <input
            type="file"
            accept=".pdf"
            style={{ display: "none" }}
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) pickFile(f);
            }}
          />
          {file ? (
            <>
              <FileText size={24} className="c-accent" />
              <span className="text-13 fw-500 c-secondary">{file.name}</span>
              <span className="text-11 c-faint">{(file.size / 1024).toFixed(0)} KB</span>
              <button
                onClick={(e) => {
                  e.preventDefault();
                  setFile(null);
                }}
                className="btn-ghost"
                style={{ position: "absolute", top: 8, right: 8, padding: 4 }}
              >
                <X size={16} />
              </button>
            </>
          ) : (
            <>
              <Upload size={28} className="c-faint" />
              <span className="text-13 c-muted">Drop your PDF here, or click to browse</span>
              <span className="text-11 c-faint">PDF only</span>
            </>
          )}
        </label>
      ) : (
        <div className="card" style={{ padding: 20 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 14 }}>
            <img
              src="/graduate-user-icon.png"
              alt=""
              className="cv-agent-badge"
              style={{ width: 28, height: 28, objectFit: "contain", borderRadius: 8, background: "var(--surface)", border: "1px solid var(--border)", padding: 4 }}
            />
            <div>
              <div className="text-13 fw-600 c-primary">{done ? "Profile ready" : "Reading your CV…"}</div>
              <div className="text-11 c-faint">{done ? "Taking you to the next step" : `Working on ${file?.name}`}</div>
            </div>
          </div>
          {LOG_LINES.map((line, i) => (
            <div
              key={line}
              className={i < visibleLines ? "fade-in-line" : ""}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 8,
                marginBottom: 8,
                opacity: i < visibleLines ? 1 : 0,
              }}
            >
              {done || i < visibleLines - 1 ? (
                <CheckCircle size={14} className="c-success" />
              ) : i === visibleLines - 1 ? (
                <span className="pulse-dot" style={{ width: 8, height: 8 }} />
              ) : (
                <span style={{ width: 14 }} />
              )}
              <span className="text-13 c-secondary">{line}</span>
              {!done && i === visibleLines - 1 && (
                <span style={{ display: "inline-flex", gap: 3, marginLeft: 2 }}>
                  <span className="chat-dot" />
                  <span className="chat-dot" style={{ animationDelay: "0.15s" }} />
                  <span className="chat-dot" style={{ animationDelay: "0.3s" }} />
                </span>
              )}
            </div>
          ))}
        </div>
      )}

      {error && (
        <p className="text-12 c-danger" style={{ marginTop: 8 }}>
          {error}
        </p>
      )}

      <div style={{ display: "flex", justifyContent: "space-between", marginTop: 24 }}>
        <button className="btn-ghost btn-ghost-sm" onClick={() => onDone(EMPTY_PROFILE)}>
          Skip and enter details manually
        </button>
        <Button variant="primary" disabled={!file || processing} onClick={submit}>
          Next →
        </Button>
      </div>
    </div>
  );
}
