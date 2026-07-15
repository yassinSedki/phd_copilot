import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "@/api/client";
import Modal from "@/components/ui/Modal";
import SegmentedControl from "@/components/ui/SegmentedControl";
import Button from "@/components/ui/Button";
import EmailChatBox from "@/components/ui/EmailChatBox";
import { stripAiDividers } from "@/lib/text";
import type {
  ReferencePreviewRequest,
  ReferencePreviewResponse,
  ReferenceRequestChatResponse,
  ReferenceRequestWithReferee,
  RefereeRead,
  SubmissionMethod,
} from "@/api/types";

const CHAT_SUGGESTIONS = ["More concise", "Less formal", "Mention the deadline", "Softer tone"];

function useDebounced<T>(value: T, ms: number): T {
  const [d, setD] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setD(value), ms);
    return () => clearTimeout(t);
  }, [value, ms]);
  return d;
}

export default function ReferenceRequestModal({ applicationId, itemId, onClose }: { applicationId: number; itemId: string; onClose: () => void }) {
  const qc = useQueryClient();
  const referees = useQuery<RefereeRead[]>({ queryKey: ["referees"], queryFn: () => api.get<RefereeRead[]>("/referees") });

  const [refereeId, setRefereeId] = useState<number | null>(null);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [title, setTitle] = useState("");
  const [method, setMethod] = useState<SubmissionMethod>("portal");
  const [note, setNote] = useState("");
  const [created, setCreated] = useState<ReferenceRequestWithReferee | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Editable copies of the drafted email — the user can type directly here
  // or use the chat box below to ask the AI to change it.
  const [subject, setSubject] = useState("");
  const [bodyText, setBodyText] = useState("");

  useEffect(() => {
    if (created) {
      setSubject(created.request.email_subject ?? "");
      setBodyText(stripAiDividers(created.request.email_body ?? ""));
    }
  }, [created?.request.id]);

  const debouncedNote = useDebounced(note, 500);
  const body: ReferencePreviewRequest | null =
    refereeId || name
      ? {
          referee_id: refereeId,
          referee_name: refereeId ? undefined : name,
          referee_title: refereeId ? undefined : title,
          application_id: applicationId,
          submission_method: method,
          personal_note: debouncedNote || null,
        }
      : null;

  const preview = useQuery<ReferencePreviewResponse>({
    queryKey: ["reference-preview", body],
    queryFn: () => api.post<ReferencePreviewResponse>("/reference-requests/preview", body!),
    enabled: !!body,
  });

  const create = useMutation({
    mutationFn: () =>
      api.post<ReferenceRequestWithReferee>(`/reference-requests?item_id=${encodeURIComponent(itemId)}`, {
        referee_id: refereeId,
        referee_name: refereeId ? undefined : name,
        referee_title: refereeId ? undefined : title,
        referee_email: refereeId ? undefined : email,
        application_id: applicationId,
        submission_method: method,
        personal_note: note || null,
      }),
    onSuccess: (data) => {
      setCreated(data);
      qc.invalidateQueries({ queryKey: ["application", applicationId] });
      qc.invalidateQueries({ queryKey: ["referees"] });
    },
    onError: (e) => setError(e instanceof ApiError ? e.message : "Could not create the request"),
  });

  const saveEdit = useMutation({
    mutationFn: () => api.patch<ReferenceRequestWithReferee>(`/reference-requests/${created!.request.id}`, { subject, body: bodyText }),
    onSuccess: (data) => setCreated(data),
    onError: (e) => setError(e instanceof ApiError ? e.message : "Could not save your changes"),
  });

  const chat = useMutation({
    mutationFn: (message: string) => api.post<ReferenceRequestChatResponse>(`/reference-requests/${created!.request.id}/chat`, { message }),
    onSuccess: (res) => {
      setSubject(res.request.email_subject ?? "");
      setBodyText(stripAiDividers(res.request.email_body ?? ""));
      setCreated({ request: res.request, referee: res.referee });
    },
    onError: (e) => setError(e instanceof ApiError ? e.message : "Could not apply that change"),
  });

  const copy = useMutation({
    mutationFn: async (req: ReferenceRequestWithReferee) => {
      await api.patch(`/reference-requests/${req.request.id}`, { subject, body: bodyText });
      await navigator.clipboard.writeText(`To: ${req.referee.email}\nSubject: ${subject}\n\n${bodyText}`);
      return api.post(`/reference-requests/${req.request.id}/copy`);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["application", applicationId] });
      onClose();
    },
  });

  const send = useMutation({
    mutationFn: async (id: number) => {
      // The backend sends whatever is persisted — save any unsaved edits
      // first so Send never mails a stale draft.
      await api.patch(`/reference-requests/${id}`, { subject, body: bodyText });
      return api.post(`/reference-requests/${id}/send`);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["application", applicationId] });
      onClose();
    },
    onError: (e) => setError(e instanceof ApiError ? e.message : "Send failed"),
  });

  return (
    <Modal
      title="Request reference letter"
      onClose={onClose}
      width={560}
      footer={
        !created ? (
          <>
            <Button variant="ghost" onClick={onClose}>
              Cancel
            </Button>
            <Button variant="primary" disabled={!refereeId && (!name || !email)} loading={create.isPending} onClick={() => create.mutate()}>
              Continue
            </Button>
          </>
        ) : (
          <>
            <Button variant="secondary" size="sm" loading={saveEdit.isPending} onClick={() => saveEdit.mutate()}>
              Save changes
            </Button>
            <Button variant="secondary" loading={copy.isPending} onClick={() => copy.mutate(created)}>
              Copy email
            </Button>
            <Button variant="primary" loading={send.isPending} onClick={() => send.mutate(created.request.id)}>
              Send
            </Button>
          </>
        )
      }
    >
      {!created ? (
        <div style={{ display: "flex", flexDirection: "column", gap: 14 }}>
          <div>
            <label className="field-label">Existing referee</label>
            <select className="input" value={refereeId ?? ""} onChange={(e) => setRefereeId(e.target.value ? Number(e.target.value) : null)}>
              <option value="">New referee…</option>
              {(referees.data ?? []).map((r) => (
                <option key={r.id} value={r.id}>
                  {r.name} ({r.email})
                </option>
              ))}
            </select>
          </div>

          {!refereeId && (
            <>
              <div>
                <label className="field-label">Referee email *</label>
                <input className="input" type="email" value={email} onChange={(e) => setEmail(e.target.value)} />
              </div>
              <div>
                <label className="field-label">Referee name *</label>
                <input className="input" value={name} onChange={(e) => setName(e.target.value)} />
              </div>
              <div>
                <label className="field-label">Title / Role</label>
                <input className="input" placeholder="Prof., Dr., ..." value={title} onChange={(e) => setTitle(e.target.value)} />
              </div>
            </>
          )}

          <div>
            <label className="field-label">Submission method</label>
            <SegmentedControl
              options={[
                { value: "portal", label: "Portal link" },
                { value: "forward_to_me", label: "Email to me" },
                { value: "other", label: "Other" },
              ]}
              value={method}
              onChange={setMethod}
            />
          </div>

          <div>
            <label className="field-label">Personal note</label>
            <textarea className="input" rows={2} placeholder="e.g. We discussed this last week" value={note} onChange={(e) => setNote(e.target.value)} />
          </div>

          <hr className="divider" />

          <div>
            <div className="text-11 fw-600 c-faint uppercase-label" style={{ marginBottom: 8 }}>
              Draft request email
            </div>
            <div className="surface-2" style={{ border: "1px solid var(--border)", borderRadius: 6, padding: "14px 16px" }}>
              {preview.data ? (
                <>
                  <div className="text-12 fw-500 c-primary" style={{ marginBottom: 8 }}>
                    {preview.data.subject}
                  </div>
                  <p className="text-13 c-secondary" style={{ lineHeight: 1.75, whiteSpace: "pre-wrap" }}>
                    {stripAiDividers(preview.data.body)}
                  </p>
                </>
              ) : (
                <p className="text-13 c-faint">Fill in the referee's name to see a preview.</p>
              )}
            </div>
          </div>

          {error && <p className="text-12 c-danger">{error}</p>}
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          <div>
            <label className="field-label">Subject</label>
            <input className="input" value={subject} onChange={(e) => setSubject(e.target.value)} />
          </div>
          <div>
            <label className="field-label">Body — edit directly, or ask the AI below</label>
            <textarea
              className="input"
              style={{ minHeight: 180, lineHeight: 1.65 }}
              value={bodyText}
              onChange={(e) => setBodyText(e.target.value)}
            />
          </div>

          {error && <p className="text-12 c-danger">{error}</p>}

          <hr className="divider" style={{ margin: "4px 0" }} />

          <EmailChatBox
            history={created.request.chat_history}
            suggestions={CHAT_SUGGESTIONS}
            loading={chat.isPending}
            onSend={(message) => chat.mutate(message)}
          />
        </div>
      )}
    </Modal>
  );
}
