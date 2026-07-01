// Mirrors the backend Pydantic schemas. Hand-written for the Phase-2 prototype;
// once stable, generate from /openapi.json instead (architecture section 5).

export type Status =
  | "NEW"
  | "REVIEWING"
  | "SHORTLISTED"
  | "DISCARDED"
  | "DRAFTING"
  | "READY"
  | "APPLIED"
  | "INTERVIEW"
  | "OFFER"
  | "REJECTED"
  | "WITHDRAWN"
  | "EXPIRED";

export const KANBAN_COLUMNS: Status[] = [
  "REVIEWING",
  "SHORTLISTED",
  "DRAFTING",
  "READY",
  "APPLIED",
  "INTERVIEW",
  "OFFER",
  "REJECTED",
];

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface MeResponse {
  id: number;
  email: string;
}

export interface Profile {
  id: number;
  user_id: number;
  full_name: string | null;
  research_summary: string | null;
  interests: string | null;
  skills: unknown[] | null;
  education: unknown[] | null;
  publications: unknown[] | null;
  languages: string | null;
  location_prefs: string | null;
  constraints: string | null;
  cv_path: string | null;
}

export type ProfileUpdate = Partial<Omit<Profile, "id" | "user_id">>;

export interface Settings {
  id: number;
  user_id: number;
  filters: Record<string, unknown> | null;
  score_threshold: number;
  scoring_model: string | null;
  drafting_model: string | null;
  schedule: string | null;
}

export type SettingsUpdate = Partial<Omit<Settings, "id" | "user_id">>;

export interface ScoreRead {
  id: number;
  score: number;
  fit_breakdown: Record<string, number> | null;
  reasons: string | null;
  red_flags: string[] | null;
  model_used: string | null;
  scored_at: string;
}

export interface ListingSummary {
  id: number;
  title: string | null;
  institution: string | null;
  country: string | null;
  city: string | null;
  research_field: string | null;
  offer_type: string | null;
  deadline: string | null;
  parsed_ok: boolean;
}

export interface ListingWithScore extends ListingSummary {
  latest_score?: ScoreRead | null;
}

export interface ListingDetail extends ListingWithScore {
  source: string;
  source_key: string;
  url: string | null;
  funding_info: string | null;
  contact_email: string | null;
  application_url: string | null;
  required_docs: string[] | null;
  description: string | null;
  first_seen: string;
  last_seen: string;
}

export interface DocsChecklistItem {
  doc: string;
  ready: boolean;
  path: string | null;
}

export interface ApplicationRead {
  id: number;
  listing_id: number;
  status: Status;
  priority: number;
  deadline: string | null;
  docs_checklist: DocsChecklistItem[] | null;
  cover_letter_path: string | null;
  applied_at: string | null;
  next_action: string | null;
  next_action_date: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
  listing: ListingSummary;
}

export interface KanbanBoard {
  columns: Record<Status, ApplicationRead[]>;
}

export interface JobRead {
  id: number;
  type: string;
  status: "queued" | "running" | "done" | "failed";
  progress: number;
  result_ref: string | null;
  error: string | null;
  created_at: string;
  finished_at: string | null;
}

export interface RunResponse {
  job_id: number;
}

export interface CoverLetterRead {
  application_id: number;
  path: string | null;
  body_markdown: string | null;
  exists: boolean;
}

export interface ContactRead {
  id: number;
  professor_name: string | null;
  institution: string | null;
  lab_url: string | null;
  email: string | null;
  research_summary: string | null;
  source_notes: string | null;
}

export interface OutreachRead {
  id: number;
  contact_id: number;
  draft_email: string | null;
  status: string;
  created_at: string;
}

export interface OutreachWithContact {
  outreach: OutreachRead;
  contact: ContactRead;
}

export interface DashboardResponse {
  counts_by_status: Record<string, number>;
  top_matches: ListingWithScore[];
  upcoming_deadlines: ApplicationRead[];
  action_needed: ApplicationRead[];
  in_progress: ApplicationRead[];
  total_listings: number;
  total_applications: number;
  last_run_at: string | null;
}
