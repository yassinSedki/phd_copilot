import { KeyboardEvent, useState } from "react";
import { X } from "lucide-react";

interface TagInputProps {
  values: string[];
  onChange: (values: string[]) => void;
  placeholder?: string;
}

export default function TagInput({ values, onChange, placeholder = "+ Add" }: TagInputProps) {
  const [draft, setDraft] = useState("");

  function commit() {
    const trimmed = draft.trim();
    if (trimmed && !values.includes(trimmed)) onChange([...values, trimmed]);
    setDraft("");
  }

  function onKeyDown(e: KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter" || e.key === ",") {
      e.preventDefault();
      commit();
    } else if (e.key === "Backspace" && !draft && values.length > 0) {
      onChange(values.slice(0, -1));
    }
  }

  return (
    <div style={{ display: "flex", flexWrap: "wrap", gap: 6, alignItems: "center" }}>
      {values.map((v) => (
        <span key={v} className="tag" style={{ cursor: "default" }}>
          {v}
          <X size={12} style={{ cursor: "pointer", color: "var(--text-faint)" }} onClick={() => onChange(values.filter((x) => x !== v))} />
        </span>
      ))}
      <input
        className="text-12"
        style={{ border: "none", background: "transparent", outline: "none", minWidth: 80 }}
        value={draft}
        onChange={(e) => setDraft(e.target.value)}
        onKeyDown={onKeyDown}
        onBlur={commit}
        placeholder={placeholder}
      />
    </div>
  );
}
