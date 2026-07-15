import { FormEvent, useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowUp, Check, Copy, Pencil, RotateCcw } from "lucide-react";
import { api, ApiError } from "@/api/client";
import Button from "@/components/ui/Button";
import ChatHistory from "@/components/ui/ChatHistory";
import { stripAiDividers } from "@/lib/text";
import CardHeader from "@/components/ui/CardHeader";
import { formatDateTime } from "@/lib/date";
import type { DocType, DocumentChatResponse, DocumentVersionRead } from "@/api/types";

const DOC_LABEL: Record<DocType, string> = {
  cover_letter: "Cover letter",
  sop: "SOP",
  research_proposal: "Research proposal",
};

const SUGGESTIONS: Record<DocType, string[]> = {
  cover_letter: ["More concise", "Less formal", "Address gaps", "Stronger opening", "Add example"],
  sop: ["Sharpen research question", "Cut generic filler", "Add methods detail"],
  research_proposal: ["Add a timeline", "Strengthen lit review", "Tighten aims"],
};

export default function DocumentEditor({ appId, docType }: { appId: number; docType: DocType }) {
  const qc = useQueryClient();
  const [message, setMessage] = useState("");
  const [historyOpen, setHistoryOpen] = useState(false);
  const [editing, setEditing] = useState(false);
  const [draftBody, setDraftBody] = useState("");
  const queryKey = ["document", appId, docType];

  const { data, isLoading } = useQuery<DocumentVersionRead>({
    queryKey,
    queryFn: () => api.get<DocumentVersionRead>(`/applications/${appId}/documents/${docType}`),
    retry: false,
  });

  useEffect(() => {
    if (data) setDraftBody(data.body_markdown);
  }, [data?.id]);

  const versions = useQuery<DocumentVersionRead[]>({
    queryKey: [...queryKey, "versions"],
    queryFn: () => api.get<DocumentVersionRead[]>(`/applications/${appId}/documents/${docType}/versions`),
    enabled: !!data,
  });

  const generate = useMutation({
    mutationFn: () => api.post<DocumentVersionRead>(`/applications/${appId}/documents/${docType}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey });
      qc.invalidateQueries({ queryKey: [...queryKey, "versions"] });
      qc.invalidateQueries({ queryKey: ["application", appId] });
    },
  });

  const [pendingAsk, setPendingAsk] = useState("");
  const chat = useMutation({
    mutationFn: (text: string) => api.post<DocumentChatResponse>(`/applications/${appId}/documents/${docType}/chat`, { message: text }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey });
      qc.invalidateQueries({ queryKey: [...queryKey, "versions"] });
    },
  });

  const revert = useMutation({
    mutationFn: (v: number) => api.post(`/applications/${appId}/documents/${docType}/versions/${v}/revert`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey });
      qc.invalidateQueries({ queryKey: [...queryKey, "versions"] });
    },
  });

  const saveEdit = useMutation({
    mutationFn: () => api.patch<DocumentVersionRead>(`/applications/${appId}/documents/${docType}`, { body_markdown: draftBody }),
    onSuccess: () => {
      setEditing(false);
      qc.invalidateQueries({ queryKey });
      qc.invalidateQueries({ queryKey: [...queryKey, "versions"] });
    },
  });

  const [copied, setCopied] = useState(false);
  async function copyBody() {
    if (!data) return;
    await navigator.clipboard.writeText(data.body_markdown);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  }

  function submit(e: FormEvent) {
    e.preventDefault();
    const text = message.trim();
    if (!text) return;
    setPendingAsk(text);
    setMessage("");
    chat.mutate(text);
  }

  if (isLoading) {
    return (
      <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center" }}>
        <p className="text-13 c-muted">Loading…</p>
      </div>
    );
  }

  if (!data) {
    return (
      <div style={{ flex: 1, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 12 }}>
        <p className="text-13 c-muted">No draft yet.</p>
        <Button variant="primary" loading={generate.isPending} onClick={() => generate.mutate()}>
          Generate {DOC_LABEL[docType]}
        </Button>
        {generate.isError && (
          <p className="text-12 c-danger">{generate.error instanceof ApiError ? generate.error.message : "Generation failed"}</p>
        )}
      </div>
    );
  }

  return (
    <>
      <CardHeader>
        <span className="tag">{DOC_LABEL[docType]}</span>
        <div style={{ flex: 1 }} />
        {editing ? (
          <>
            <Button variant="ghost" size="sm" onClick={() => { setEditing(false); setDraftBody(data.body_markdown); }}>
              Cancel
            </Button>
            <Button variant="primary" size="sm" loading={saveEdit.isPending} onClick={() => saveEdit.mutate()}>
              Save
            </Button>
          </>
        ) : (
          <button className="btn-ghost" style={{ padding: 6 }} title="Edit directly" onClick={() => setEditing(true)}>
            <Pencil size={14} />
          </button>
        )}
        <button className="btn-ghost" style={{ padding: 6 }} title="Copy to clipboard" onClick={copyBody}>
          {copied ? <Check size={14} /> : <Copy size={14} />}
        </button>
        <div style={{ position: "relative" }}>
          <button className="btn-ghost" style={{ padding: 6 }} title="History" onClick={() => setHistoryOpen((v) => !v)}>
            <RotateCcw size={14} />
          </button>
          {historyOpen && (
            <div
              className="card"
              style={{
                position: "absolute",
                top: "calc(100% + 4px)",
                right: 0,
                minWidth: 220,
                zIndex: 30,
                boxShadow: "var(--shadow-float)",
              }}
            >
              {(versions.data ?? []).map((v) => (
                <div
                  key={v.version_number}
                  className="tr menu-item"
                  style={{ padding: "8px 12px", justifyContent: "space-between", gap: 8 }}
                >
                  <span className="text-12 c-faint">{formatDateTime(v.created_at)}</span>
                  <button
                    className="text-12 c-accent"
                    style={{ background: "none", border: "none", cursor: "pointer" }}
                    onClick={() => {
                      revert.mutate(v.version_number);
                      setHistoryOpen(false);
                    }}
                  >
                    Restore
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </CardHeader>

      <div style={{ flex: 1, padding: "20px 24px", overflowY: "auto" }}>
        {editing ? (
          <textarea
            className="input"
            style={{ width: "100%", height: "100%", minHeight: 300, lineHeight: 1.75, fontSize: 14, resize: "vertical" }}
            value={draftBody}
            onChange={(e) => setDraftBody(e.target.value)}
            autoFocus
          />
        ) : (
          <div className="text-14 c-primary" style={{ lineHeight: 1.75 }}>
            {stripAiDividers(data.body_markdown)
              .split(/\n\s*\n/)
              .map((block, i) => (
                <p key={i} style={{ margin: 0, marginBottom: 12, whiteSpace: "pre-wrap" }}>
                  {block}
                </p>
              ))}
          </div>
        )}
      </div>

      <div style={{ borderTop: "1px solid var(--border)", padding: "12px 16px", opacity: editing ? 0.4 : 1, pointerEvents: editing ? "none" : undefined }}>
        {editing && (
          <p className="text-11 c-faint" style={{ marginBottom: 8 }}>
            Finish editing above (Save or Cancel) to ask the AI for a change.
          </p>
        )}
        {data.chat_history.length === 0 && (
          <div className="no-scrollbar" style={{ display: "flex", gap: 6, overflowX: "auto", marginBottom: 8 }}>
            {SUGGESTIONS[docType].map((s) => (
              <span key={s} className="chip tr" style={{ cursor: "pointer" }} onClick={() => setMessage(s)}>
                {s}
              </span>
            ))}
          </div>
        )}

        <ChatHistory turns={data.chat_history} thinking={chat.isPending} pendingUserMessage={pendingAsk} />

        <form onSubmit={submit} style={{ display: "flex", gap: 6 }}>
          <input className="input" style={{ flex: 1 }} placeholder="Refine this document..." value={message} onChange={(e) => setMessage(e.target.value)} />
          <Button type="submit" variant="primary" square loading={chat.isPending}>
            <ArrowUp size={14} />
          </Button>
        </form>
      </div>
    </>
  );
}
