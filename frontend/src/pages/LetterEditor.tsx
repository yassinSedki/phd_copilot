import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "@/api/client";
import type { CoverLetterRead } from "@/api/types";

export default function LetterEditor() {
  const { id } = useParams();
  const appId = Number(id);
  const qc = useQueryClient();
  const [body, setBody] = useState("");
  const [saveMsg, setSaveMsg] = useState<string | null>(null);

  const { data, isLoading } = useQuery<CoverLetterRead>({
    queryKey: ["letter", appId],
    queryFn: () => api.get<CoverLetterRead>(`/applications/${appId}/letter`),
    enabled: !isNaN(appId),
  });

  useEffect(() => {
    if (data?.body_markdown) setBody(data.body_markdown);
  }, [data]);

  const save = useMutation({
    mutationFn: (text: string) =>
      api.put<CoverLetterRead>(`/applications/${appId}/letter`, { body_markdown: text }),
    onSuccess: () => {
      setSaveMsg("Saved.");
      qc.invalidateQueries({ queryKey: ["letter", appId] });
      setTimeout(() => setSaveMsg(null), 1500);
    },
    onError: (e) => setSaveMsg(e instanceof ApiError ? e.message : "Save failed"),
  });

  if (isLoading) return <p className="text-slate-500">Loading…</p>;
  if (!data) return null;

  if (!data.exists) {
    return (
      <div className="space-y-3">
        <h1 className="text-2xl font-semibold">Cover letter</h1>
        <p className="text-slate-600">No draft yet for this application.</p>
        <Link to={`/tracker/${appId}`} className="btn-secondary inline-block">
          Back — generate a draft from the application page
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Cover letter</h1>
        <div className="flex items-center gap-2">
          <Link to={`/tracker/${appId}`} className="btn-secondary">
            Back to application
          </Link>
          <a
            href={`/api/applications/${appId}/letter/download`}
            className="btn-secondary"
          >
            Download .md
          </a>
          <button
            className="btn-primary"
            onClick={() => save.mutate(body)}
            disabled={save.isPending}
          >
            {save.isPending ? "Saving…" : "Save"}
          </button>
        </div>
      </div>
      {saveMsg && <p className="text-sm text-emerald-600">{saveMsg}</p>}

      <div className="grid lg:grid-cols-2 gap-4">
        <textarea
          className="input font-mono text-sm h-[70vh]"
          value={body}
          onChange={(e) => setBody(e.target.value)}
        />
        <div className="card prose prose-slate max-w-none whitespace-pre-wrap h-[70vh] overflow-auto">
          {body}
        </div>
      </div>

      <p className="text-xs text-slate-500">
        Phase-3 prototype renders Markdown only. PDF rendering with Typst lands in the worker container (Phase 5).
        Until then, "Download .md" gives you a plain-text Markdown file you can convert with any tool.
      </p>
    </div>
  );
}
