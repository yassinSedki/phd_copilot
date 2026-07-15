/**
 * Deadline readouts: plain-English state ("Due today", "Due in 5 days",
 * "Deadline passed") instead of a cryptic "D-n" countdown, colored by
 * urgency. --urgent under 7 days, --warning under 21, neutral otherwise.
 */
function daysUntil(date: string): number {
  return Math.ceil((new Date(date).getTime() - Date.now()) / (1000 * 60 * 60 * 24));
}

export function deadlineLabel(days: number): string {
  if (days < 0) return "Deadline passed";
  if (days === 0) return "Due today";
  if (days === 1) return "Due tomorrow";
  return `Due in ${days} days`;
}

export type DeadlineTier = "passed" | "urgent" | "warning" | "neutral";

/** Single source of the urgency thresholds — DeadlineText and DeadlineBadge
 * used to duplicate the <7/<21 cutoffs with two color mechanisms. */
export function deadlineTier(days: number): DeadlineTier {
  if (days < 0) return "passed";
  if (days < 7) return "urgent";
  if (days < 21) return "warning";
  return "neutral";
}

const TIER_COLOR: Record<DeadlineTier, string> = {
  passed: "var(--ink-tertiary)",
  urgent: "var(--urgent)",
  warning: "var(--warning)",
  neutral: "var(--ink-secondary)",
};

export function deadlineColor(days: number): string {
  return TIER_COLOR[deadlineTier(days)];
}

export default function DeadlineText({
  deadline,
  withIcon = false,
  dateOnly = false,
}: {
  deadline: string | null;
  withIcon?: boolean;
  /** Table columns: show just the calendar date, colored by urgency — the
   * relative phrase ("Due in N days") is available on hover instead of
   * taking up column width on every row. */
  dateOnly?: boolean;
}) {
  if (!deadline) return null;
  const days = daysUntil(deadline);
  const date = new Date(deadline).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });

  if (dateOnly) {
    return (
      <span className="data text-13" style={{ color: deadlineColor(days), whiteSpace: "nowrap" }} title={deadlineLabel(days)}>
        {date}
      </span>
    );
  }

  return (
    <span className="data text-12" style={{ color: deadlineColor(days), whiteSpace: "nowrap" }} title={date}>
      {deadlineLabel(days)}
      {withIcon && <span style={{ color: "var(--ink-tertiary)", marginLeft: 8 }}>{date}</span>}
    </span>
  );
}

export { daysUntil };
