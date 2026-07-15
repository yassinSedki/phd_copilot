import type { Status } from "@/api/types";

const LABEL: Record<Status, string> = {
  SAVED: "Saved",
  IN_PROGRESS: "In progress",
  DOCS_READY: "Docs ready",
  APPLIED: "Applied",
  INTERVIEW: "Interview",
  OFFER: "Offer",
  REJECTED: "Rejected",
  WITHDRAWN: "Withdrawn",
};

// One distinct hue per lifecycle stage — a status column should read at a
// glance without deciphering labels (see .status-* pills in index.css).
const CLASS: Record<Status, string> = {
  SAVED: "status-saved",
  IN_PROGRESS: "status-progress",
  DOCS_READY: "status-docs",
  APPLIED: "status-applied",
  INTERVIEW: "status-interview",
  OFFER: "status-offer",
  REJECTED: "status-rejected",
  WITHDRAWN: "status-withdrawn",
};

export default function StatusTag({ status }: { status: Status }) {
  return <span className={`status-tag ${CLASS[status]}`}>{LABEL[status]}</span>;
}

export { LABEL as STATUS_LABEL };
