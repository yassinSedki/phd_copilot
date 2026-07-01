import { FormEvent, useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "@/api/client";
import type { JobRead, OutreachWithContact, RunResponse } from "@/api/types";

export default function DeepDive() {
  const { outreachId } = useParams();
  const navigate = useNavigate();
  const qc = useQueryClient();

  const [professor, setProfessor] = useState("");
  const [institution, setInstitution] = useState("");
  const [labUrl, setLabUrl] = useState("");
  const [topic, setTopic] = useState("");
  const [jobId, setJobId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  const list = useQuery<OutreachWithContact[]>({
    queryKey: ["outreach"],
    queryFn: () => api.get<OutreachWithContact[]>("/outreach"),
  });

  const selected = useQuery<OutreachWithContact>({
    queryKey: ["outreach", outreachId],
    queryFn: () => api.get<OutreachWithContact>(`/deepdive/${outreachId}`),
    enabled: !!outreachId,
  });

  const start = useMutation({
    mutationFn: () =>
      api.post<RunResponse>("/deepdive", {
        professor_name: professor,
        institution: institution || null,
        lab_url: labUrl || null,
        topic: topic || null,
      }),
    onSuccess: (r) => setJobId(r.job_id),
    onError: (e) => setError(e instanceof ApiError ? e.message : "Deep-dive failed to start"),
  });

  const job = useQuery<JobRead>({
    enabled: jobId !== null,
    queryKey: ["job", jobId],
    queryFn: () => api.get<JobRead>(`/jobs/${jobId}`),
    refetchInterval: (q) => {
      const d = q.state.data;
      if (!d) return 800;
      return d.status === "done" || d.status === "failed" ? false : 800;
    },
  });

  useEffect(() => {
    if (job.data?.status === "done") {
      qc.invalidateQueries({ queryKey: ["outreach"] });
      // result_ref looks like "outreach_id=12 contact_id=4"
      const m = job.data.result_ref?.match(/outreach_id=(\d+)/);
      if (m) {
        const id = m[1];
        setJobId(null);
        navigate(`/deepdive/${id}`);
      }
    }
  }, [job.data, navigate, qc]);

  function submit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    start.mutate();
  }

  return (
    <div className="grid md:grid-cols-[2fr_1fr] gap-6">
      <div className="space-y-4">
        <h1 className="text-2xl font-semibold">Deep-dive</h1>
        <p className="text-sm text-slate-600">
          One lab at a time. The platform researches the group and drafts a personalised outreach email — you edit and send it
          yourself. Section 12 / 16 of the architecture explains the rules.
        </p>

        <form onSubmit={submit} className="card space-y-3">
          <div className="grid md:grid-cols-2 gap-3">
            <div>
              <label className="label">Professor name *</label>
              <input className="input" value={professor} onChange={(e) => setProfessor(e.target.value)} required />
            </div>
            <div>
              <label className="label">Institution</label>
              <input className="input" value={institution} onChange={(e) => setInstitution(e.target.value)} />
            </div>
            <div className="md:col-span-2">
              <label className="label">Lab URL</label>
              <input className="input" value={labUrl} onChange={(e) => setLabUrl(e.target.value)} />
            </div>
            <div className="md:col-span-2">
              <label className="label">Topic (optional)</label>
              <input className="input" value={topic} onChange={(e) => setTopic(e.target.value)} />
            </div>
          </div>
          {error && <p className="text-sm text-rose-600">{error}</p>}
          <div className="flex justify-end">
            <button className="btn-primary" type="submit" disabled={start.isPending}>
              {start.isPending ? "Starting…" : "Research & draft"}
            </button>
          </div>
        </form>

        {job.data && job.data.status !== "done" && (
          <div className="card">
            <div className="flex items-center justify-between text-sm">
              <span>Job #{job.data.id}</span>
              <span className="text-slate-500">{job.data.status}</span>
            </div>
            <div className="h-2 bg-slate-100 rounded mt-2">
              <div className="h-2 bg-brand-500 rounded" style={{ width: `${job.data.progress}%` }} />
            </div>
          </div>
        )}

        {selected.data && <SelectedOutreach data={selected.data} />}
      </div>

      <aside className="space-y-3">
        <h2 className="font-medium">Recent drafts</h2>
        {list.data && list.data.length > 0 ? (
          <ul className="space-y-2">
            {list.data.map((o) => (
              <li key={o.outreach.id}>
                <button
                  onClick={() => navigate(`/deepdive/${o.outreach.id}`)}
                  className="card w-full text-left hover:border-brand-500"
                >
                  <div className="font-medium text-sm">{o.contact.professor_name}</div>
                  <div className="text-xs text-slate-500">{o.contact.institution}</div>
                  <div className="text-xs text-slate-400 mt-1">{o.outreach.status} · {new Date(o.outreach.created_at).toLocaleDateString()}</div>
                </button>
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-slate-500">No drafts yet.</p>
        )}
      </aside>
    </div>
  );
}

function SelectedOutreach({ data }: { data: OutreachWithContact }) {
  const qc = useQueryClient();
  const [email, setEmail] = useState(data.contact.email ?? "");
  const [draft, setDraft] = useState(data.outreach.draft_email ?? "");
  const [msg, setMsg] = useState<string | null>(null);

  useEffect(() => {
    setEmail(data.contact.email ?? "");
    setDraft(data.outreach.draft_email ?? "");
  }, [data.outreach.id, data.contact.email, data.outreach.draft_email]);

  const save = useMutation({
    mutationFn: (body: { draft_email?: string; email?: string; status?: string }) =>
      api.patch<OutreachWithContact>(`/outreach/${data.outreach.id}`, body),
    onSuccess: () => {
      setMsg("Saved.");
      qc.invalidateQueries({ queryKey: ["outreach"] });
      qc.invalidateQueries({ queryKey: ["outreach", String(data.outreach.id)] });
      setTimeout(() => setMsg(null), 1500);
    },
  });

  return (
    <div className="space-y-3">
      <div className="card space-y-2">
        <h3 className="font-medium">{data.contact.professor_name}</h3>
        <p className="text-sm text-slate-600">{data.contact.institution}</p>
        {data.contact.lab_url && (
          <a href={data.contact.lab_url} target="_blank" rel="noreferrer" className="text-sm text-brand-600 hover:underline">
            {data.contact.lab_url}
          </a>
        )}
        <div className="text-sm whitespace-pre-wrap text-slate-700">{data.contact.research_summary}</div>
        {data.contact.source_notes && (
          <details className="text-xs text-slate-500">
            <summary>Research notes</summary>
            <pre className="whitespace-pre-wrap">{data.contact.source_notes}</pre>
          </details>
        )}
      </div>

      <div className="card space-y-3">
        <h3 className="font-medium">Contact email (manually confirmed only)</h3>
        <input
          type="email"
          className="input"
          placeholder="prof@example.org"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
        />
        <p className="text-xs text-slate-500">
          Section 16: only store an email you've verified yourself. We never scrape email addresses to bulk-contact.
        </p>
      </div>

      <div className="card space-y-3">
        <h3 className="font-medium">Draft email</h3>
        <textarea className="input font-mono text-sm h-72" value={draft} onChange={(e) => setDraft(e.target.value)} />
        <div className="flex items-center justify-between">
          <span className="text-xs text-slate-500">Status: {data.outreach.status}</span>
          <div className="flex gap-2">
            <button
              className="btn-secondary"
              disabled={save.isPending}
              onClick={() => save.mutate({ draft_email: draft, email: email || undefined })}
            >
              Save draft
            </button>
            <button
              className="btn-primary"
              disabled={save.isPending}
              onClick={() => save.mutate({ status: "SENT_BY_USER", draft_email: draft, email: email || undefined })}
            >
              Mark sent (by me)
            </button>
          </div>
        </div>
        {msg && <p className="text-xs text-emerald-600">{msg}</p>}
      </div>
    </div>
  );
}
