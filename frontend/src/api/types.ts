// Mirrors backend Pydantic schemas (backend/app/schemas/*.py).

export type Status =
  | "SAVED"
  | "IN_PROGRESS"
  | "DOCS_READY"
  | "APPLIED"
  | "INTERVIEW"
  | "OFFER"
  | "REJECTED"
  | "WITHDRAWN";

export const ALLOWED_TRANSITIONS: Record<Status, Status[]> = {
  SAVED: ["IN_PROGRESS", "REJECTED", "WITHDRAWN"],
  IN_PROGRESS: ["DOCS_READY", "SAVED", "REJECTED", "WITHDRAWN"],
  DOCS_READY: ["APPLIED", "IN_PROGRESS", "WITHDRAWN"],
  APPLIED: ["INTERVIEW", "REJECTED", "WITHDRAWN"],
  INTERVIEW: ["OFFER", "REJECTED", "WITHDRAWN"],
  OFFER: ["REJECTED"],
  REJECTED: [],
  WITHDRAWN: [],
};

export const ALL_STATUSES: Status[] = [
  "SAVED",
  "IN_PROGRESS",
  "DOCS_READY",
  "APPLIED",
  "INTERVIEW",
  "OFFER",
  "REJECTED",
  "WITHDRAWN",
];

// ---------- Auth ----------

export interface TokenResponse {
  access_token: string;
  token_type: string;
  is_onboarded: boolean;
}

export interface MeResponse {
  id: number;
  email: string;
  full_name: string | null;
  is_onboarded: boolean;
}

// ---------- Onboarding ----------

export interface ExtractedProfile {
  full_name: string | null;
  email: string | null;
  phone: string | null;
  research_summary: string | null;
  research_areas: string[];
  methods: string[];
  programming_languages: string[];
  degree_subject: string | null;
  graduation_year: number | null;
  career_stage: string | null;
  languages_spoken: string[];
  publications: Record<string, unknown>[];
  geographic_hints: string[];
}

export type FundingRequired = "yes" | "no" | "preferred";
export type StartDateWindow = "0-3m" | "3-6m" | "6-12m" | "flexible";
export type ApplicationType = "phd" | "postdoc" | "both";

export interface OnboardingConstraintsBody {
  funding_required?: FundingRequired | null;
  countries?: string[] | null;
  start_date_window?: StartDateWindow | null;
  application_type?: ApplicationType | null;
  hard_constraints_text?: string | null;
}

// ---------- Profile / Settings ----------

export interface Profile {
  id: number;
  user_id: number;
  full_name: string | null;
  contact_email: string | null;
  phone: string | null;
  research_summary: string | null;
  interests: string | null;
  skills: unknown[] | null;
  education: unknown[] | null;
  publications: unknown[] | null;
  languages: string | null;
  location_prefs: string | null;
  constraints: string | null;
  cv_path: string | null;
  cv_filename: string | null;
  cv_text: string | null;
  cv_sha256: string | null;
  profile_constraints: OnboardingConstraintsBody | null;
  is_onboarded: boolean;
}

export type ProfileUpdate = Partial<Omit<Profile, "id" | "user_id">>;

export interface UserSettings {
  id: number;
  user_id: number;
  filters: Record<string, unknown> | null;
  score_threshold: number;
  scoring_model: string | null;
  drafting_model: string | null;
  schedule: string | null;
}

// ---------- Jobs / search runs ----------

export interface JobProgressMeta {
  url?: string;
  current_url?: string;
  pages_processed?: number;
  listings_found?: number;
  listings_kept_by_prefilter?: number;
  listings_matched?: number;
  currently_checking?: string;
  needs_continue_prompt?: boolean;
  rendering?: string;
  duplicates_skipped?: number;
  dropped_by_prefilter?: string[];
  empty_reason?: string;
  current_step?: string;
  checkpoint?: { pages: number; found: number; kept: number; discarded: number };
  /** Why a paused (awaiting_continue) run paused: "page_limit" means the
   * per-run safety ceiling was hit but more pages exist; anything else (or
   * absent) means the periodic checkpoint. */
  pause_reason?: string | null;
  /** Why a run that finished WITHOUT pausing has nothing more:
   * "exhausted" (no next-page link found — fully explored), "loop_detected"
   * (site started repeating), "no_results" (a page came back empty). */
  stop_reason?: string | null;
}

/** Snapshot of a finished search, kept client-side so the dashboard can
 * explain what happened after the live job disappears. */
export interface SearchResultSummary {
  url: string;
  status: "done" | "failed" | "cancelled";
  found: number;
  kept: number;
  matched: number;
  duplicates: number;
  pagesProcessed: number;
  stopReason: string | null;
  droppedReasons: string[];
  emptyReason: string | null;
  error: string | null;
}

export interface JobRead {
  id: number;
  type: string;
  status: "queued" | "running" | "awaiting_continue" | "done" | "failed" | "cancelled";
  progress: number;
  progress_meta: JobProgressMeta | null;
  result_ref: string | null;
  error: string | null;
  created_at: string;
  finished_at: string | null;
}

export interface RunResponse {
  job_id: number;
  search_run_id: number | null;
}

export interface SearchRunRead {
  id: number;
  url: string;
  status: "queued" | "running" | "awaiting_continue" | "done" | "cancelled" | "failed";
  pages_processed: number;
  listings_found: number;
  listings_matched: number;
  job_id: number | null;
  created_at: string;
  finished_at: string | null;
}

// ---------- Dashboard ----------

export type UrgencyKind = "deadline_near" | "letter_ready_to_send" | "reference_overdue" | "reference_due_soon";

export interface UrgencyItem {
  kind: UrgencyKind;
  application_id: number;
  title: string;
  institution: string | null;
  days_until: number;
  cta: { label: string; href: string };
}

export interface RecentSearchItem {
  id: number;
  url: string;
  status: string;
  listings_matched: number;
  created_at: string;
}

export interface LastRun {
  search_run_id: number | null;
  finished_at: string | null;
  listings_matched: number | null;
  summary: string;
}

export interface DashboardStats {
  opportunities: number;
  avg_match: number | null;
  applications: number;
  interviews: number;
  offers: number;
  upcoming_deadlines: number;
  excellent_matches: number;
}

export interface PipelineStage {
  key: string;
  label: string;
  count: number;
}

export interface FeaturedOpportunity {
  listing_id: number;
  application_id: number | null;
  title: string;
  institution: string | null;
  score: number;
  funding_type: FundingType;
  deadline: string | null;
  days_until_deadline: number | null;
}

export type NextActionKind = "deadline" | "docs" | "reference" | "cv" | "generic";

export interface NextAction {
  label: string;
  href: string;
  kind: NextActionKind;
}

export interface DashboardResponse {
  urgent: UrgencyItem[];
  recent_searches: RecentSearchItem[];
  last_run: LastRun;
  stats: DashboardStats;
  pipeline: PipelineStage[];
  featured: FeaturedOpportunity | null;
  next_actions: NextAction[];
}

// ---------- Listings ----------

export interface ScoreRead {
  id: number;
  score: number;
  fit_breakdown: Record<string, number> | null;
  reasons: string | null;
  red_flags: string[] | null;
  model_used: string | null;
  fit_paragraph: string | null;
  scored_at: string;
}

export interface FitExplanation {
  paragraph: string;
}

export type FundingType = "fully_funded" | "partial" | "unknown";

export interface ListingRow {
  id: number;
  title: string | null;
  institution: string | null;
  country: string | null;
  city: string | null;
  research_field: string | null;
  offer_type: string | null;
  deadline: string | null;
  parsed_ok: boolean;
  latest_score: ScoreRead | null;
  supervisor_name: string | null;
  funding_type: FundingType;
  status: Status | null;
  application_id: number | null;
}

export interface ListingDetail extends ListingRow {
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

// ---------- Applications ----------

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

export type ChecklistItemKind = "document" | "manual" | "reference" | "portal";

export interface DocsChecklistItem {
  id: string;
  kind: ChecklistItemKind;
  label: string;
  ready: boolean;
  doc_type?: string | null;
  url?: string | null;
  referee_id?: number | null;
  reference_request_id?: number | null;
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

export interface ReferenceCounts {
  requested: number;
  required: number;
}

export interface ApplicationRow {
  id: number;
  title: string | null;
  institution: string | null;
  supervisor_name: string | null;
  deadline: string | null;
  status: Status;
  priority: number;
  cover_letter_status: "draft" | "refined" | "done" | null;
  sop_status: string | null;
  references: ReferenceCounts;
  readiness_score: number;
  notes_preview: string | null;
}

export interface ApplicationListResponse {
  items: ApplicationRow[];
  total: number;
}

export type BulkActionRequest =
  | { ids: number[]; action: "set_status"; status: Status }
  | { ids: number[]; action: "archive" };

export interface BulkResultItem {
  id: number;
  ok: boolean;
  error: string | null;
}

export interface BulkActionResponse {
  results: BulkResultItem[];
}

// ---------- Documents ----------

export interface ChatTurn {
  role: "user" | "assistant";
  content: string;
  at: string | null;
}

export type DocType = "cover_letter" | "sop" | "research_proposal";

export interface DocumentVersionRead {
  id: number;
  application_id: number;
  doc_type: DocType;
  version_number: number;
  body_markdown: string;
  created_by: "user" | "agent";
  chat_history: ChatTurn[];
  author_notes: string | null;
  warnings: string[];
  created_at: string;
}

export interface DocumentChatResponse {
  version: DocumentVersionRead;
  assistant_reply: string;
}

// ---------- Deep research / outreach ----------

export interface PublicationRef {
  title: string;
}

export interface ContactRead {
  id: number;
  professor_name: string | null;
  institution: string | null;
  lab_url: string | null;
  email: string | null;
  research_summary: string | null;
  source_notes: string | null;
  publications: PublicationRef[];
}

/** Ask-the-AI-to-revise turn for email drafts (outreach / reference
 * requests) — lighter than the document ChatTurn (no `at` timestamp). */
export interface EmailChatTurn {
  role: "user" | "assistant";
  content: string;
}

export interface OutreachRead {
  id: number;
  contact_id: number;
  draft_email: string | null;
  email_subject: string | null;
  email_body: string | null;
  status: "DRAFT" | "SENT";
  sent_at: string | null;
  chat_history: EmailChatTurn[];
  created_at: string;
}

export interface OutreachWithContact {
  outreach: OutreachRead;
  contact: ContactRead;
}

export interface OutreachChatResponse {
  outreach: OutreachRead;
  contact: ContactRead;
  assistant_reply: string;
}

// ---------- Referees / reference requests ----------

export interface RefereeRead {
  id: number;
  name: string;
  title: string | null;
  institution: string | null;
  email: string;
  relationship_type: string | null;
  notes: string | null;
  request_count: number;
  created_at: string;
  updated_at: string;
}

export interface RefereeCreate {
  name: string;
  title?: string | null;
  institution?: string | null;
  email: string;
  relationship_type?: string | null;
  notes?: string | null;
}

export type SubmissionMethod = "portal" | "forward_to_me" | "other";

export interface ReferenceRequestRead {
  id: number;
  referee_id: number;
  application_id: number;
  status: "draft" | "sent" | "received" | "overdue";
  submission_method: SubmissionMethod;
  email_subject: string | null;
  email_body: string | null;
  chat_history: EmailChatTurn[];
  sent_at: string | null;
  due_at: string | null;
  follow_up_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface ReferenceRequestWithReferee {
  request: ReferenceRequestRead;
  referee: RefereeRead;
}

export interface ReferenceRequestEdit {
  subject?: string | null;
  body?: string | null;
}

export interface ReferenceRequestChatResponse {
  request: ReferenceRequestRead;
  referee: RefereeRead;
  assistant_reply: string;
}

export interface ReferencePreviewRequest {
  referee_id?: number | null;
  referee_name?: string | null;
  referee_title?: string | null;
  referee_email?: string | null;
  application_id: number;
  submission_method: SubmissionMethod;
  personal_note?: string | null;
}

export interface ReferencePreviewResponse {
  subject: string;
  body: string;
}
