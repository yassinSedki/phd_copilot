import { deadlineLabel, deadlineTier } from "./DeadlineText";

const TIER_CLASS: Record<ReturnType<typeof deadlineTier>, string> = {
  passed: "badge-neutral",
  urgent: "badge-danger",
  warning: "badge-warning",
  neutral: "badge-neutral",
};

/** Deadline Register chip: mono D-n countdown, colored by urgency. */
export default function DeadlineBadge({ days }: { days: number }) {
  return <span className={`badge ${TIER_CLASS[deadlineTier(days)]}`}>{deadlineLabel(days)}</span>;
}
