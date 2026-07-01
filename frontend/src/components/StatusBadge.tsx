import type { Status } from "@/api/types";

const colors: Record<Status, string> = {
  NEW: "bg-slate-100 text-slate-700",
  REVIEWING: "bg-sky-100 text-sky-800",
  SHORTLISTED: "bg-indigo-100 text-indigo-800",
  DISCARDED: "bg-slate-200 text-slate-600",
  DRAFTING: "bg-violet-100 text-violet-800",
  READY: "bg-amber-100 text-amber-800",
  APPLIED: "bg-emerald-100 text-emerald-800",
  INTERVIEW: "bg-teal-100 text-teal-800",
  OFFER: "bg-lime-100 text-lime-800",
  REJECTED: "bg-rose-100 text-rose-800",
  WITHDRAWN: "bg-slate-100 text-slate-500",
  EXPIRED: "bg-slate-100 text-slate-500",
};

export default function StatusBadge({ status }: { status: Status }) {
  return <span className={`pill ${colors[status] ?? "bg-slate-100 text-slate-700"}`}>{status}</span>;
}
