const DIVIDER_LINE = /^\s*([-*_])(\s*\1){2,}\s*$/;

/** Strips markdown divider lines ("---", "***", "___") that models leave
 * behind as an AI-generated-content tell — mirrors
 * shared/llm/types.py::strip_ai_dividers on the backend. Backend output is
 * cleaned at the source now; this catches any version saved before that
 * fix, or text rendered elsewhere in the UI. */
export function stripAiDividers(text: string): string {
  if (!text) return text;
  const lines = text.split("\n").filter((line) => !DIVIDER_LINE.test(line));
  const out: string[] = [];
  let blankRun = 0;
  for (const line of lines) {
    if (line.trim() === "") {
      blankRun += 1;
      if (blankRun > 1) continue;
    } else {
      blankRun = 0;
    }
    out.push(line);
  }
  return out.join("\n").trim();
}
