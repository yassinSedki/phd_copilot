import { CSSProperties, useEffect, useRef, useState } from "react";
import { stripAiDividers } from "@/lib/text";

function AgentBadge() {
  return (
    <span
      style={{
        width: 20,
        height: 20,
        borderRadius: 6,
        background: "var(--surface)",
        border: "1px solid var(--border)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        flexShrink: 0,
        marginTop: 2,
      }}
    >
      <img src="/graduate-user-icon.png" alt="AI" style={{ width: 13, height: 13, objectFit: "contain" }} />
    </span>
  );
}

const assistantBubbleStyle: CSSProperties = {
  background: "var(--surface-2)",
  borderRadius: "10px 10px 10px 2px",
  padding: "7px 11px",
  maxWidth: "85%",
  lineHeight: 1.6,
};

/** Types the newest assistant reply out progressively so the answer feels
 * streamed rather than appearing all at once. Only animates turns that
 * arrive after mount — history loaded from the server renders instantly. */
function AssistantText({ content, animate, onTick }: { content: string; animate: boolean; onTick?: () => void }) {
  const clean = stripAiDividers(content);
  const [shown, setShown] = useState(animate ? 0 : clean.length);
  useEffect(() => {
    if (!animate) return;
    setShown(0);
    const step = Math.max(2, Math.round(clean.length / 90)); // ~1.5s total
    const id = setInterval(() => {
      setShown((n) => {
        const next = n + step;
        if (next >= clean.length) clearInterval(id);
        return next;
      });
      onTick?.();
    }, 16);
    return () => clearInterval(id);
  }, [clean, animate]);
  return <>{clean.slice(0, shown)}</>;
}

/** Shared rendering for a refine-chat transcript: user asks on the right in
 * a bubble, assistant replies on the left in a soft card with an AI marker.
 * While `thinking`, shows the in-flight user message and a pulsing-dots
 * bubble; the reply that follows streams in with a typing animation. */
export default function ChatHistory({
  turns,
  maxHeight = 140,
  thinking = false,
  pendingUserMessage,
}: {
  turns: { role: "user" | "assistant"; content: string }[];
  maxHeight?: number;
  thinking?: boolean;
  pendingUserMessage?: string;
}) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const mountedTurnCount = useRef(turns.length);
  const scrollToEnd = () => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  };
  useEffect(scrollToEnd, [turns.length, thinking]);

  if (turns.length === 0 && !thinking) return null;
  const lastIndex = turns.length - 1;

  return (
    <div
      ref={scrollRef}
      style={{ maxHeight, overflowY: "auto", marginBottom: 8, display: "flex", flexDirection: "column", gap: 8 }}
    >
      {turns.map((turn, i) =>
        turn.role === "user" ? (
          <div key={i} style={{ display: "flex", justifyContent: "flex-end" }}>
            <span
              className="text-13"
              style={{
                background: "var(--accent)",
                color: "var(--primary-contrast)",
                borderRadius: "10px 10px 2px 10px",
                padding: "6px 11px",
                maxWidth: "80%",
                lineHeight: 1.5,
              }}
            >
              {turn.content}
            </span>
          </div>
        ) : (
          <div key={i} style={{ display: "flex", justifyContent: "flex-start", gap: 8 }}>
            <AgentBadge />
            <div className="text-13 c-secondary" style={assistantBubbleStyle}>
              <AssistantText
                content={turn.content}
                animate={i === lastIndex && i >= mountedTurnCount.current}
                onTick={scrollToEnd}
              />
            </div>
          </div>
        )
      )}

      {thinking && (
        <>
          {pendingUserMessage && (
            <div style={{ display: "flex", justifyContent: "flex-end" }}>
              <span
                className="text-13"
                style={{
                  background: "var(--accent)",
                  color: "var(--primary-contrast)",
                  borderRadius: "10px 10px 2px 10px",
                  padding: "6px 11px",
                  maxWidth: "80%",
                  lineHeight: 1.5,
                }}
              >
                {pendingUserMessage}
              </span>
            </div>
          )}
          <div style={{ display: "flex", justifyContent: "flex-start", gap: 8 }}>
            <AgentBadge />
            <div style={{ ...assistantBubbleStyle, display: "flex", gap: 4, alignItems: "center", padding: "10px 12px" }}>
              <span className="chat-dot" />
              <span className="chat-dot" style={{ animationDelay: "0.15s" }} />
              <span className="chat-dot" style={{ animationDelay: "0.3s" }} />
            </div>
          </div>
        </>
      )}
    </div>
  );
}
