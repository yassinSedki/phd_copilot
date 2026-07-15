import { FormEvent, useState } from "react";
import { ArrowUp } from "lucide-react";
import Button from "./Button";
import ChatHistory from "./ChatHistory";
import type { EmailChatTurn } from "@/api/types";

/** "Ask the AI to change it" box for a subject+body email draft — same
 * shape as the document chat in DocumentEditor, reused for supervisor
 * outreach and reference-request drafts so both get the same capability. */
export default function EmailChatBox({
  history,
  suggestions,
  onSend,
  loading,
}: {
  history: EmailChatTurn[];
  suggestions?: string[];
  onSend: (message: string) => void;
  loading: boolean;
}) {
  const [message, setMessage] = useState("");
  const [lastSent, setLastSent] = useState("");

  function submit(e: FormEvent) {
    e.preventDefault();
    const trimmed = message.trim();
    if (!trimmed) return;
    setLastSent(trimmed);
    onSend(trimmed);
    setMessage("");
  }

  return (
    <div>
      {history.length === 0 && suggestions && suggestions.length > 0 && (
        <div className="no-scrollbar" style={{ display: "flex", gap: 6, overflowX: "auto", marginBottom: 8 }}>
          {suggestions.map((s) => (
            <span key={s} className="chip tr" style={{ cursor: "pointer" }} onClick={() => setMessage(s)}>
              {s}
            </span>
          ))}
        </div>
      )}

      <ChatHistory turns={history} maxHeight={120} thinking={loading} pendingUserMessage={lastSent} />

      <form onSubmit={submit} style={{ display: "flex", gap: 6 }}>
        <input
          className="input"
          style={{ flex: 1 }}
          placeholder="Ask the AI to change it — e.g. 'make it more concise'"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
        />
        <Button type="submit" variant="primary" square loading={loading}>
          <ArrowUp size={14} />
        </Button>
      </form>
    </div>
  );
}
