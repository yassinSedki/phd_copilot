import { FormEvent, useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowUpRight, CheckCircle, AlertTriangle, Mail, Send, Trash2, Users } from "lucide-react";
import { api, ApiError } from "@/api/client";
import { useJobProgress } from "@/hooks/useJobProgress";
import Button from "@/components/ui/Button";
import CardHeader from "@/components/ui/CardHeader";
import ConfirmDialog from "@/components/ui/ConfirmDialog";
import EmailChatBox from "@/components/ui/EmailChatBox";
import { formatDate, formatDateTime } from "@/lib/date";
import { stripAiDividers } from "@/lib/text";
import type { OutreachChatResponse, OutreachWithContact, PublicationRef, RunResponse } from "@/api/types";

const OUTREACH_CHAT_SUGGESTIONS = ["More concise", "Less formal", "Mention a specific publication", "Shorter subject line"];

// Ordered to match the agent's STEP_LABELS (worker research_graph) — the UI
// checks off REAL steps from the job's progress meta, not a timed animation.
const AGENT_STEPS = [
  "Finding the lab page",
  "Reading the lab page",
  "Extracting research themes",
  "Finding recent publications",
  "Identifying overlap with your profile",
  "Drafting the outreach email",
  "Checking the draft cites real work",
];

function isGeneric(body: string, publications: PublicationRef[]): boolean {
  const lower = body.toLowerCase();
  const hasPub = publications.some((p) => p.title && lower.includes(p.title.toLowerCase().slice(0, 20)));
  const hasNumbers = /\b(20\d{2}|[0-9]+%)\b/.test(body);
  return !hasPub && !hasNumbers;
}

export default function Supervisors() {
  const [searchParams] = useSearchParams();
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [showForm, setShowForm] = useState(false);
  const [confirmingDeleteId, setConfirmingDeleteId] = useState<number | null>(null);
  const qc = useQueryClient();

  const list = useQuery<OutreachWithContact[]>({ queryKey: ["outreach"], queryFn: () => api.get<OutreachWithContact[]>("/outreach") });

  const remove = useMutation({
    mutationFn: (id: number) => api.delete(`/outreach/${id}`),
    onSuccess: (_data, id) => {
      qc.invalidateQueries({ queryKey: ["outreach"] });
      if (selectedId === id) setSelectedId(null);
    },
  });
  const selected = useQuery<OutreachWithContact>({
    queryKey: ["outreach", selectedId],
    queryFn: () => api.get<OutreachWithContact>(`/deepdive/${selectedId}`),
    enabled: selectedId !== null,
  });

  useEffect(() => {
    if (searchParams.get("professor")) setShowForm(true);
  }, [searchParams]);

  return (
    <div>
      <h1 className="text-20 fw-600 c-primary" style={{ marginBottom: 24 }}>
        Supervisors
      </h1>
      <div style={{ display: "flex", gap: 20 }}>
        <div className="card" style={{ width: 300, flexShrink: 0, overflow: "hidden" }}>
          <CardHeader>
            <span className="text-12 fw-600 c-faint uppercase-label" style={{ flex: 1 }}>
              Previous research
            </span>
            <Button
              variant="primary"
              size="sm"
              onClick={() => {
                setSelectedId(null);
                setShowForm(true);
              }}
            >
              + New
            </Button>
          </CardHeader>
          {list.isLoading ? (
            <div>
              {[1, 2, 3].map((i) => (
                <div key={i} style={{ padding: "12px 20px", borderBottom: "1px solid var(--border)" }}>
                  <div className="skeleton" style={{ width: "70%", height: 14, marginBottom: 6 }} />
                  <div className="skeleton" style={{ width: "50%", height: 11, marginBottom: 4 }} />
                  <div className="skeleton" style={{ width: "35%", height: 10 }} />
                </div>
              ))}
            </div>
          ) : !list.data || list.data.length === 0 ? (
            <div style={{ padding: 24, textAlign: "center" }}>
              <p className="text-13 c-faint">No research yet</p>
            </div>
          ) : (
            list.data.map((o) => (
              <div
                key={o.outreach.id}
                className="tr"
                role="button"
                tabIndex={0}
                style={{
                  padding: "12px 20px",
                  borderBottom: "1px solid var(--border)",
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "flex-start",
                  gap: 8,
                  background: selectedId === o.outreach.id ? "var(--accent-light)" : undefined,
                  borderLeft: selectedId === o.outreach.id ? "3px solid var(--accent)" : "3px solid transparent",
                }}
                onClick={() => {
                  setSelectedId(o.outreach.id);
                  setShowForm(false);
                }}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    setSelectedId(o.outreach.id);
                    setShowForm(false);
                  }
                }}
              >
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div className="text-13 fw-500 c-secondary">{o.contact.professor_name}</div>
                  <div className="text-12 c-faint" style={{ marginTop: 2 }}>
                    {o.contact.institution}
                  </div>
                  <div className="text-11 c-faint" style={{ marginTop: 2 }}>
                    {formatDate(o.outreach.created_at)}
                  </div>
                </div>
                <button
                  className="btn-ghost"
                  style={{ padding: 4, flexShrink: 0 }}
                  title="Delete"
                  aria-label="Delete supervisor research"
                  onClick={(e) => {
                    e.stopPropagation();
                    setConfirmingDeleteId(o.outreach.id);
                  }}
                >
                  <Trash2 size={14} className="c-faint" />
                </button>
              </div>
            ))
          )}
        </div>

        <div className="card" style={{ flex: 1, display: "flex", flexDirection: "column", minHeight: 500 }}>
          {showForm ? (
            <NewResearchForm
              onStarted={() => setShowForm(false)}
              onDone={(id) => {
                setSelectedId(id);
                setShowForm(false);
              }}
            />
          ) : selected.data ? (
            <ResearchResults data={selected.data} />
          ) : (
            <div style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 8 }}>
              <Users size={40} className="c-faint" />
              <p className="text-13 c-muted">Select a supervisor or start new research.</p>
            </div>
          )}
        </div>
      </div>

      {confirmingDeleteId !== null && (
        <ConfirmDialog
          title="Delete this research?"
          message="This professor's research, drafted email, and chat history will be permanently removed. This can't be undone."
          confirmLabel="Delete"
          loading={remove.isPending}
          onConfirm={() => {
            remove.mutate(confirmingDeleteId);
            setConfirmingDeleteId(null);
          }}
          onClose={() => setConfirmingDeleteId(null)}
        />
      )}
    </div>
  );
}

function NewResearchForm({ onStarted, onDone }: { onStarted: () => void; onDone: (outreachId: number) => void }) {
  const [searchParams] = useSearchParams();
  const qc = useQueryClient();
  const [professor, setProfessor] = useState(searchParams.get("professor") ?? "");
  const [institution, setInstitution] = useState(searchParams.get("institution") ?? "");
  const [labUrl, setLabUrl] = useState("");
  const [topic, setTopic] = useState(searchParams.get("topic") ?? "");
  const [note, setNote] = useState("");
  const [jobId, setJobId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  const start = useMutation({
    mutationFn: () =>
      api.post<RunResponse>("/deepdive", {
        professor_name: professor,
        institution: institution || null,
        lab_url: labUrl || null,
        topic: topic || null,
        personal_note: note || null,
      }),
    onSuccess: (r) => {
      setJobId(r.job_id);
      onStarted();
    },
    onError: (e) => setError(e instanceof ApiError ? e.message : "Failed to start"),
  });

  const { data: job } = useJobProgress(jobId);
  const [justFinished, setJustFinished] = useState(false);

  useEffect(() => {
    if (job?.status === "done" && !justFinished) {
      qc.invalidateQueries({ queryKey: ["outreach"] });
      // A visible "finished" beat before jumping to the results — without
      // this the panel just silently swaps, easy to miss that the agent
      // actually completed rather than the page simply having reloaded.
      setJustFinished(true);
      const m = job.result_ref?.match(/outreach_id=(\d+)/);
      const timer = setTimeout(() => {
        if (m) onDone(Number(m[1]));
      }, 1100);
      return () => clearTimeout(timer);
    }
  }, [job?.status]);

  function submit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    start.mutate();
  }

  if (jobId && job && job.status !== "failed") {
    if (job.status !== "done" || justFinished) {
      // Render the agent's REAL progress: the worker streams its current step
      // into the job meta; everything before it is done, everything after is
      // pending. (This used to be a setTimeout animation unrelated to reality.)
      const currentStep = job.progress_meta?.current_step;
      const activeIndex = justFinished ? AGENT_STEPS.length : currentStep ? AGENT_STEPS.indexOf(currentStep) : 0;
      const pct = Math.round((Math.max(0, activeIndex) / AGENT_STEPS.length) * 100);
      return (
        <div style={{ padding: 24 }} aria-live="polite">
          {justFinished ? (
            <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 10, padding: "32px 0" }}>
              <CheckCircle size={28} className="c-success" />
              <div className="text-14 fw-500 c-primary">Research complete</div>
              <div className="text-12 c-faint">Opening the drafted email…</div>
            </div>
          ) : (
            <>
              <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 16 }}>
                <span className="pulse-dot" />
                <span className="text-13 fw-600 c-primary">Agent researching</span>
                <span className="text-12 c-faint truncate" style={{ maxWidth: 220 }}>
                  {professor}{institution ? ` · ${institution}` : ""}
                </span>
              </div>
              {AGENT_STEPS.map((line, i) => {
                const state = i < activeIndex ? "done" : i === activeIndex ? "active" : "pending";
                return (
                  <div key={line} style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 8, opacity: state === "pending" ? 0.35 : 1 }}>
                    {state === "done" ? (
                      <CheckCircle size={14} className="c-success" />
                    ) : state === "active" ? (
                      <span className="pulse-dot" style={{ width: 8, height: 8 }} />
                    ) : (
                      <span style={{ width: 14 }} />
                    )}
                    <span className={state === "active" ? "text-13 shimmer-text" : "text-13 c-secondary"}>{line}</span>
                  </div>
                );
              })}
              <div className="agent-progress" style={{ marginTop: 16 }}>
                <div className="agent-progress-fill" style={{ width: `${Math.max(4, pct)}%` }} />
              </div>
              <p className="text-12 c-faint" style={{ marginTop: 10, lineHeight: 1.5 }}>
                Reading the lab page and cross-referencing your profile can take a minute — the draft is grounded in
                real publications, not a template.
              </p>
            </>
          )}
        </div>
      );
    }
  }

  return (
    <form onSubmit={submit} style={{ padding: 24, display: "flex", flexDirection: "column", gap: 14 }}>
      <div>
        <label className="field-label">Professor name *</label>
        <input className="input" value={professor} onChange={(e) => setProfessor(e.target.value)} required />
      </div>
      <div>
        <label className="field-label">Institution *</label>
        <input className="input" value={institution} onChange={(e) => setInstitution(e.target.value)} />
      </div>
      <div>
        <label className="field-label">Lab URL (optional)</label>
        <input className="input" value={labUrl} onChange={(e) => setLabUrl(e.target.value)} />
      </div>
      <div>
        <label className="field-label">PhD topic / position (optional)</label>
        <input className="input" value={topic} onChange={(e) => setTopic(e.target.value)} />
      </div>
      <div>
        <label className="field-label">Personal connection (optional)</label>
        <textarea className="input" rows={3} placeholder="e.g. I attended your NeurIPS 2024 talk on meta-learning..." value={note} onChange={(e) => setNote(e.target.value)} />
      </div>
      {error && <p className="text-12 c-danger">{error}</p>}
      {job?.status === "failed" && (
        <p className="text-12 c-danger">The research run failed. Try again, or add a lab URL to skip the lookup step.</p>
      )}
      <div style={{ display: "flex", justifyContent: "flex-end" }}>
        <Button type="submit" variant="primary" loading={start.isPending}>
          Research this supervisor →
        </Button>
      </div>
    </form>
  );
}

function ResearchResults({ data }: { data: OutreachWithContact }) {
  const qc = useQueryClient();
  const [email, setEmail] = useState(data.contact.email ?? "");
  const [subject, setSubject] = useState(data.outreach.email_subject ?? "");
  const [body, setBody] = useState(stripAiDividers(data.outreach.email_body ?? ""));
  const [msg, setMsg] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setEmail(data.contact.email ?? "");
    setSubject(data.outreach.email_subject ?? "");
    setBody(stripAiDividers(data.outreach.email_body ?? ""));
    setError(null);
  }, [data.outreach.id]);

  const saveEmail = useMutation({
    mutationFn: () => api.post(`/outreach/${data.outreach.id}/save-email`, { subject, body }),
    onSuccess: () => {
      setMsg("Saved.");
      qc.invalidateQueries({ queryKey: ["outreach"] });
      setTimeout(() => setMsg(null), 1500);
    },
  });
  const saveRecipient = useMutation({
    mutationFn: (v: string) => api.patch(`/outreach/${data.outreach.id}`, { email: v }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["outreach"] }),
  });

  const copy = useMutation({
    mutationFn: async () => {
      await navigator.clipboard.writeText(`To: ${email}\nSubject: ${subject}\n\n${body}`);
      return api.post(`/outreach/${data.outreach.id}/copy`);
    },
    onSuccess: () => {
      setMsg("Copied.");
      qc.invalidateQueries({ queryKey: ["outreach"] });
      setTimeout(() => setMsg(null), 1500);
    },
  });

  const send = useMutation({
    mutationFn: async () => {
      // The backend sends whatever is persisted, not the request body — make
      // sure the current edits are saved first so "Send" never mails a stale draft.
      await api.post(`/outreach/${data.outreach.id}/save-email`, { subject, body });
      return api.post(`/outreach/${data.outreach.id}/send`);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["outreach"] });
      qc.invalidateQueries({ queryKey: ["outreach", data.outreach.id] });
    },
    onError: (e) => setError(e instanceof ApiError ? e.message : "Send failed"),
  });

  const chat = useMutation({
    mutationFn: (message: string) => api.post<OutreachChatResponse>(`/outreach/${data.outreach.id}/chat`, { message }),
    onSuccess: (res) => {
      setSubject(res.outreach.email_subject ?? "");
      setBody(stripAiDividers(res.outreach.email_body ?? ""));
      qc.setQueryData(["outreach", data.outreach.id], { outreach: res.outreach, contact: res.contact });
      qc.invalidateQueries({ queryKey: ["outreach"] });
    },
    onError: (e) => setError(e instanceof ApiError ? e.message : "Could not apply that change"),
  });

  const wordCount = body.trim() ? body.trim().split(/\s+/).length : 0;
  const generic = isGeneric(body, data.contact.publications);
  const sent = data.outreach.status === "SENT";

  return (
    <div style={{ display: "flex", flex: 1 }}>
      <div style={{ flex: 1, padding: 20, borderRight: "1px solid var(--border)" }}>
        <div className="text-16 fw-600 c-primary">{data.contact.professor_name}</div>
        <div className="text-12 c-faint" style={{ marginBottom: 4 }}>
          {data.contact.institution}
        </div>
        {data.contact.lab_url && (
          <a href={data.contact.lab_url} target="_blank" rel="noreferrer" className="text-12 c-accent" style={{ display: "inline-flex", alignItems: "center", gap: 4, marginBottom: 20 }}>
            Lab page <ArrowUpRight size={12} />
          </a>
        )}

        <div className="text-11 fw-600 c-faint uppercase-label" style={{ marginBottom: 8 }}>
          Research themes
        </div>
        <div style={{ display: "flex", flexWrap: "wrap", gap: 4, marginBottom: 16 }}>
          {(data.contact.source_notes?.match(/Topics:\n([\s\S]*?)(\n\n|$)/)?.[1].split("\n") ?? []).map(
            (t) => t.replace(/^- /, "").trim()
          ).filter(Boolean).map((t) => (
            <span key={t} className="tag">
              {t}
            </span>
          ))}
        </div>

        <div className="text-11 fw-600 c-faint uppercase-label" style={{ marginBottom: 8 }}>
          Recent publications
        </div>
        {data.contact.publications.slice(0, 4).map((p, i) => (
          <div key={i} style={{ display: "flex", gap: 8, marginBottom: 10 }}>
            <span style={{ width: 2, height: 12, background: "var(--border-strong)", borderRadius: 1, flexShrink: 0, marginTop: 2 }} />
            <span className="text-13 fw-500 c-secondary">{p.title}</span>
          </div>
        ))}

        <div className="text-11 fw-600 c-faint uppercase-label" style={{ marginBottom: 8 }}>
          Overlap with your profile
        </div>
        <p className="surface-2 text-13 c-secondary" style={{ lineHeight: 1.65, padding: 12, borderRadius: 6, border: "1px solid var(--border)" }}>
          {data.contact.research_summary}
        </p>
      </div>

      <div style={{ flex: 1, padding: 20 }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 12 }}>
          <div className="text-11 fw-600 c-faint uppercase-label">Draft email</div>
          {sent && (
            <span className="text-11 c-success" style={{ display: "flex", alignItems: "center", gap: 4 }}>
              <CheckCircle size={12} />
              Sent{data.outreach.sent_at ? ` ${formatDateTime(data.outreach.sent_at)}` : ""}
            </span>
          )}
        </div>

        <div style={{ marginBottom: 4 }}>
          <label className="field-label">To (manually confirmed)</label>
          <input className="input" type="email" value={email} onChange={(e) => setEmail(e.target.value)} onBlur={() => saveRecipient.mutate(email)} />
        </div>

        <div style={{ marginTop: 12, marginBottom: 12 }}>
          <label className="text-10 c-faint" style={{ display: "block", marginBottom: 4 }}>
            Subject
          </label>
          <input className="input" value={subject} onChange={(e) => setSubject(e.target.value)} />
        </div>

        <textarea
          className="input"
          style={{ minHeight: 220, lineHeight: 1.75 }}
          value={body}
          onChange={(e) => setBody(e.target.value)}
        />

        <div style={{ display: "flex", gap: 16, alignItems: "center", marginTop: 8 }}>
          <span className={`text-11 ${wordCount > 200 ? "c-warning" : "c-faint"}`}>{wordCount} words</span>
          {generic ? (
            <span className="text-11 c-warning" style={{ display: "flex", alignItems: "center", gap: 4 }}>
              <AlertTriangle size={12} /> No paper mentioned
            </span>
          ) : (
            <span className="text-11 c-success" style={{ display: "flex", alignItems: "center", gap: 4 }}>
              <CheckCircle size={12} /> Mentions a paper
            </span>
          )}
        </div>

        {!email && <p className="text-11 c-warning" style={{ marginTop: 8 }}>Add the professor's email above before sending.</p>}
        {error && <p className="text-11 c-danger" style={{ marginTop: 8 }}>{error}</p>}
        {msg && <p className="text-11 c-success" style={{ marginTop: 4 }}>{msg}</p>}

        <div style={{ display: "flex", gap: 8, justifyContent: "flex-end", marginTop: 12 }}>
          <Button variant="secondary" size="sm" loading={saveEmail.isPending} onClick={() => saveEmail.mutate()}>
            Save draft
          </Button>
          <Button variant="secondary" size="sm" icon={<Mail size={14} />} loading={copy.isPending} disabled={!email} onClick={() => copy.mutate()}>
            {sent ? "Copy again" : "Copy email"}
          </Button>
          <Button variant="primary" size="sm" icon={<Send size={14} />} loading={send.isPending} disabled={!email} onClick={() => send.mutate()}>
            {sent ? "Send again" : "Send"}
          </Button>
        </div>

        <hr className="divider" style={{ margin: "16px 0" }} />

        <EmailChatBox
          history={data.outreach.chat_history}
          suggestions={OUTREACH_CHAT_SUGGESTIONS}
          loading={chat.isPending}
          onSend={(message) => chat.mutate(message)}
        />
      </div>
    </div>
  );
}
