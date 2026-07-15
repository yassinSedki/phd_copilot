import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, Circle, FileText, Filter, Sparkles, Target, Trash2, UploadCloud, UserRound } from "lucide-react";
import { api, ApiError } from "@/api/client";
import CardHeader from "@/components/ui/CardHeader";
import Button from "@/components/ui/Button";
import SegmentedControl from "@/components/ui/SegmentedControl";
import TagInput from "@/components/ui/TagInput";
import type {
  ApplicationType,
  ExtractedProfile,
  FundingRequired,
  MeResponse,
  OnboardingConstraintsBody,
  Profile,
  StartDateWindow,
  UserSettings,
} from "@/api/types";

function initials(name: string | null, email: string | undefined): string {
  const source = (name || "").trim() || (email || "");
  const parts = source.split(/[\s._@]+/).filter(Boolean);
  if (parts.length === 0) return "?";
  return (parts[0][0] + (parts[1]?.[0] ?? "")).toUpperCase();
}

/** Same synthesis the onboarding review step uses, so a CV reupload here
 * produces the same kind of research summary a fresh signup would get. */
function summarizeAreas(areas: string[], degree: string | null): string {
  if (!areas.length && !degree) return "";
  const a = areas.slice(0, 3).join(", ");
  if (degree && a) return `Background in ${degree}, focused on ${a}.`;
  return a ? `Focused on ${a}.` : `Background in ${degree}.`;
}

function SectionCard({
  title,
  icon,
  titleColor,
  borderColor,
  children,
}: {
  title: string;
  icon: React.ReactNode;
  titleColor?: string;
  borderColor?: string;
  children: React.ReactNode;
}) {
  return (
    <div className="card card-hover tr" style={{ marginBottom: 20, overflow: "hidden", borderColor }}>
      <CardHeader>
        <span style={{ display: "flex", alignItems: "center", gap: 9, color: titleColor ?? "var(--text-secondary)" }}>
          {icon}
          <span className="text-13 fw-600">{title}</span>
        </span>
      </CardHeader>
      <div style={{ padding: 22 }}>{children}</div>
    </div>
  );
}

function Row({ label, description, children }: { label: string; description?: string; children: React.ReactNode }) {
  return (
    <div style={{ display: "flex", alignItems: "center", minHeight: 44, borderBottom: "1px solid var(--border)", padding: "10px 0", gap: 16 }}>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div className="text-13 fw-500 c-secondary">{label}</div>
        {description && (
          <div className="text-12 c-faint" style={{ marginTop: 2, lineHeight: 1.5 }}>
            {description}
          </div>
        )}
      </div>
      <div style={{ flexShrink: 0 }}>{children}</div>
    </div>
  );
}

/** Editable name/summary/interests — what the scorer and prefilter compare
 * every listing against. Mounted only once profile data exists so local
 * state can initialize from it. */
function ResearchProfileEditor({ profile }: { profile: Profile }) {
  const qc = useQueryClient();
  const [fullName, setFullName] = useState(profile.full_name ?? "");
  const [summary, setSummary] = useState(profile.research_summary ?? "");
  const [interests, setInterests] = useState(profile.interests ?? "");
  const [saved, setSaved] = useState(false);

  const save = useMutation({
    mutationFn: () => api.put("/profile", { full_name: fullName || null, research_summary: summary, interests }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["profile"] });
      qc.invalidateQueries({ queryKey: ["me"] });
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    },
  });

  return (
    <div>
      <label className="field-label">Full name</label>
      <input className="input" value={fullName} onChange={(e) => setFullName(e.target.value)} placeholder="Your name" />

      <p className="text-12 c-faint" style={{ margin: "16px 0 12px", lineHeight: 1.5 }}>
        Every listing is scored against the text below, so keep it an accurate, specific picture of your research.
      </p>
      <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between" }}>
        <label className="field-label">Research summary</label>
        <span className="text-11 c-faint">{summary.length} chars</span>
      </div>
      <textarea
        className="input"
        rows={8}
        style={{ minHeight: 160, lineHeight: 1.6, resize: "vertical" }}
        value={summary}
        onChange={(e) => setSummary(e.target.value)}
        placeholder="What you work on, methods you use, notable projects or publications, what you're looking for next…"
      />
      <label className="field-label" style={{ marginTop: 14 }}>
        Interests
      </label>
      <textarea
        className="input"
        rows={3}
        style={{ lineHeight: 1.6, resize: "vertical" }}
        value={interests}
        onChange={(e) => setInterests(e.target.value)}
        placeholder="e.g. NLP, retrieval-augmented generation, ML for healthcare"
      />
      <div style={{ display: "flex", alignItems: "center", gap: 10, marginTop: 14 }}>
        <Button variant="primary" size="sm" loading={save.isPending} onClick={() => save.mutate()}>
          Save profile
        </Button>
        {saved && <span className="text-12 c-success">Saved</span>}
      </div>
    </div>
  );
}

/** Editable hard search constraints — exactly what the prefilter enforces,
 * so the user can see and change why listings get filtered out. */
function ConstraintsEditor({ profile }: { profile: Profile }) {
  const qc = useQueryClient();
  const initial = profile.profile_constraints ?? {};
  const [funding, setFunding] = useState<FundingRequired | null>(initial.funding_required ?? null);
  const [countries, setCountries] = useState<string[]>(initial.countries ?? []);
  const [window, setWindow] = useState<StartDateWindow | null>(initial.start_date_window ?? null);
  const [appType, setAppType] = useState<ApplicationType | null>(initial.application_type ?? null);
  const [hardText, setHardText] = useState(initial.hard_constraints_text ?? "");
  const [saved, setSaved] = useState(false);

  const save = useMutation({
    mutationFn: () => {
      const body: OnboardingConstraintsBody = {
        funding_required: funding,
        countries,
        start_date_window: window,
        application_type: appType,
        hard_constraints_text: hardText || null,
      };
      return api.post("/onboarding/constraints", body);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["profile"] });
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    },
  });

  return (
    <div>
      <p className="text-12 c-faint" style={{ marginBottom: 12, lineHeight: 1.5 }}>
        Listings that clearly violate these are filtered out before scoring. If searches keep coming back
        empty, this is the first place to loosen. An empty country list means anywhere.
      </p>
      <Row label="Position type">
        <SegmentedControl
          options={[
            { value: "phd", label: "PhD" },
            { value: "postdoc", label: "Postdoc" },
            { value: "both", label: "Both" },
          ]}
          value={appType}
          onChange={(v) => setAppType(v as ApplicationType)}
        />
      </Row>
      <Row label="Funding" description="“Required” filters out unfunded positions">
        <SegmentedControl
          options={[
            { value: "yes", label: "Required" },
            { value: "preferred", label: "Preferred" },
            { value: "no", label: "Any" },
          ]}
          value={funding}
          onChange={(v) => setFunding(v as FundingRequired)}
        />
      </Row>
      <Row label="Start date">
        <SegmentedControl
          options={[
            { value: "0-3m", label: "0–3 mo" },
            { value: "3-6m", label: "3–6 mo" },
            { value: "6-12m", label: "6–12 mo" },
            { value: "flexible", label: "Flexible" },
          ]}
          value={window}
          onChange={(v) => setWindow(v as StartDateWindow)}
        />
      </Row>
      <div style={{ padding: "12px 0", borderBottom: "1px solid var(--border)" }}>
        <div className="text-13 fw-500 c-secondary" style={{ marginBottom: 6 }}>
          Countries
        </div>
        <TagInput values={countries} onChange={setCountries} placeholder="Add a country and press Enter. Leave empty for anywhere" />
      </div>
      <div style={{ padding: "12px 0" }}>
        <div className="text-13 fw-500 c-secondary" style={{ marginBottom: 6 }}>
          Anything else that must hold
        </div>
        <input
          className="input"
          value={hardText}
          onChange={(e) => setHardText(e.target.value)}
          placeholder="e.g. English-taught programs only"
        />
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 10, marginTop: 4 }}>
        <Button variant="primary" size="sm" loading={save.isPending} onClick={() => save.mutate()}>
          Save constraints
        </Button>
        {saved && <span className="text-12 c-success">Saved. Applies to your next search</span>}
      </div>
    </div>
  );
}

/** Contact email/phone as extracted from the CV (or typed manually) — kept
 * separate from the account's login email. Auto-saves on blur, same
 * pattern as the score-threshold field below. */
function ContactFieldsEditor({ profile }: { profile: Profile }) {
  const qc = useQueryClient();
  const save = useMutation({
    mutationFn: (patch: { contact_email?: string; phone?: string }) => api.put("/profile", patch),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["profile"] }),
  });

  return (
    <>
      <Row label="Contact email" description="Shown on drafted documents — from your CV, or type your own">
        <input
          className="input"
          style={{ width: 220 }}
          type="email"
          key={profile.contact_email ?? ""}
          defaultValue={profile.contact_email ?? ""}
          placeholder="you@example.com"
          onBlur={(e) => save.mutate({ contact_email: e.target.value })}
        />
      </Row>
      <Row label="Phone">
        <input
          className="input"
          style={{ width: 220 }}
          key={profile.phone ?? ""}
          defaultValue={profile.phone ?? ""}
          placeholder="+1 555 0100"
          onBlur={(e) => save.mutate({ phone: e.target.value })}
        />
      </Row>
    </>
  );
}

function ChecklistRow({ done, label }: { done: boolean; label: string }) {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 8, padding: "6px 0" }}>
      {done ? <CheckCircle2 size={15} className="c-success" /> : <Circle size={15} className="c-faint" />}
      <span className={`text-13 ${done ? "c-secondary" : "c-faint"}`}>{label}</span>
    </div>
  );
}

/** Mirrors the real layout's shape (identity strip + section cards) so the
 * page doesn't jump when data arrives — plain "Loading…" text would still
 * flash the empty-state copy underneath for a frame; skeleton bars never
 * look like "you have no profile yet". */
function SettingsSkeleton() {
  return (
    <div style={{ maxWidth: 1080 }}>
      <div className="skeleton" style={{ width: 100, height: 22, marginBottom: 10 }} />
      <div className="skeleton" style={{ width: 320, height: 14, marginBottom: 20 }} />

      <div className="card" style={{ display: "flex", alignItems: "center", gap: 16, padding: "18px 22px", marginBottom: 20 }}>
        <div className="skeleton" style={{ width: 48, height: 48, borderRadius: "50%", flexShrink: 0 }} />
        <div style={{ flex: 1 }}>
          <div className="skeleton" style={{ width: 160, height: 16, marginBottom: 8 }} />
          <div className="skeleton" style={{ width: 200, height: 12 }} />
        </div>
      </div>

      <div style={{ display: "flex", gap: 24, alignItems: "flex-start" }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          {[96, 220, 140, 60].map((h, i) => (
            <div key={i} className="card" style={{ marginBottom: 20, padding: 22 }}>
              <div className="skeleton" style={{ width: 120, height: 14, marginBottom: 16 }} />
              <div className="skeleton" style={{ width: "100%", height: h, borderRadius: 8 }} />
            </div>
          ))}
        </div>
        <div style={{ width: 280, flexShrink: 0 }}>
          <div className="card" style={{ padding: 20 }}>
            <div className="skeleton" style={{ width: 100, height: 12, marginBottom: 14 }} />
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="skeleton" style={{ width: "80%", height: 12, marginBottom: 10 }} />
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

export default function Settings() {
  const qc = useQueryClient();
  const me = useQuery<MeResponse>({ queryKey: ["me"], queryFn: () => api.get<MeResponse>("/auth/me") });
  const profile = useQuery<Profile>({ queryKey: ["profile"], queryFn: () => api.get<Profile>("/profile") });
  const settings = useQuery<UserSettings>({ queryKey: ["settings"], queryFn: () => api.get<UserSettings>("/settings") });

  const [showExtracted, setShowExtracted] = useState(false);
  const [cvNotice, setCvNotice] = useState<string | null>(null);

  const updateSettings = useMutation({
    mutationFn: (body: Partial<UserSettings>) => api.put("/settings", body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["settings"] }),
  });

  // Reuploading now re-runs extraction (same endpoint onboarding uses) and
  // fills in whatever profile fields are still empty — previously this
  // called /profile/cv, which only stores the file and never touched the
  // profile, so the extracted name/areas were silently discarded.
  const uploadCv = useMutation({
    mutationFn: async (file: File) => {
      const form = new FormData();
      form.append("file", file);
      const extracted = await api.postForm<ExtractedProfile>("/onboarding/cv", form);
      const current = profile.data;
      const patch: Record<string, unknown> = {};
      if (!current?.full_name && extracted.full_name) patch.full_name = extracted.full_name;
      if (!current?.contact_email && extracted.email) patch.contact_email = extracted.email;
      if (!current?.phone && extracted.phone) patch.phone = extracted.phone;
      if (!current?.interests && extracted.research_areas.length) patch.interests = extracted.research_areas.join(", ");
      if (!current?.research_summary) {
        // Prefer the LLM's own multi-sentence summary (grounded in the full
        // CV) — the templated one-liner is only a fallback for the offline
        // stub provider, which can't generate real prose.
        const summary = extracted.research_summary || summarizeAreas(extracted.research_areas, extracted.degree_subject);
        if (summary) patch.research_summary = summary;
      }
      if (Object.keys(patch).length > 0) {
        await api.put("/profile", patch);
        return "Profile updated from your new CV.";
      }
      return "CV replaced. Your profile text was left as-is — edit it below if needed.";
    },
    onSuccess: (message) => {
      setCvNotice(message);
      qc.invalidateQueries({ queryKey: ["profile"] });
      qc.invalidateQueries({ queryKey: ["me"] });
      setTimeout(() => setCvNotice(null), 6000);
    },
    onError: (e) => {
      setCvNotice(e instanceof ApiError ? e.message : "Could not process that file.");
      setTimeout(() => setCvNotice(null), 6000);
    },
  });

  const name = profile.data?.full_name || me.data?.full_name || null;
  const completeness = [
    { label: "CV uploaded", done: !!profile.data?.cv_filename },
    { label: "Research summary written", done: !!profile.data?.research_summary },
    { label: "Search constraints set", done: !!profile.data?.profile_constraints },
    { label: "Contact email set", done: !!profile.data?.contact_email },
  ];
  const completedCount = completeness.filter((c) => c.done).length;

  // Show a skeleton, not the empty-state defaults, while the first fetch is
  // in flight — otherwise "Add your name below" / "0/4" / an empty CV
  // dropzone flash on every load, indistinguishable from a genuinely empty
  // profile.
  if (me.isLoading || profile.isLoading || settings.isLoading) {
    return <SettingsSkeleton />;
  }

  return (
    <div style={{ maxWidth: 1080 }}>
      <h1 className="text-20 fw-600 c-primary">Settings</h1>
      <p className="text-13 c-muted" style={{ marginTop: 4, marginBottom: 20 }}>
        Manage your profile, research focus, and search constraints.
      </p>

      {/* Identity strip — fills the header width instead of leaving it bare */}
      <div className="card" style={{ display: "flex", alignItems: "center", gap: 16, padding: "18px 22px", marginBottom: 20 }}>
        <div
          className="data"
          style={{
            width: 48,
            height: 48,
            borderRadius: "50%",
            background: "var(--primary-soft)",
            color: "var(--primary)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: 16,
            flexShrink: 0,
          }}
        >
          {initials(name, me.data?.email)}
        </div>
        <div style={{ minWidth: 0, flex: 1 }}>
          <div className="text-16 fw-600 c-primary truncate">{name || "Add your name below"}</div>
          <div className="text-13 c-faint truncate">{me.data?.email}</div>
        </div>
        <div style={{ textAlign: "right", flexShrink: 0 }}>
          <div className="data text-20 c-primary">{completedCount}/{completeness.length}</div>
          <div className="uppercase-label c-faint">Profile setup</div>
        </div>
      </div>

      <div style={{ display: "flex", gap: 24, alignItems: "flex-start" }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <SectionCard title="Profile" icon={<UserRound size={15} />}>
            <div style={{ paddingBottom: 16, marginBottom: 16, borderBottom: "1px solid var(--border)" }}>
              {profile.data?.cv_filename ? (
                <div style={{ display: "flex", alignItems: "flex-start", gap: 12 }}>
                  <div
                    style={{
                      width: 38,
                      height: 38,
                      borderRadius: 8,
                      background: "var(--surface-sunken)",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      flexShrink: 0,
                    }}
                  >
                    <FileText size={17} className="c-muted" />
                  </div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <span className="text-13 fw-500 c-secondary truncate" style={{ display: "block" }}>
                      {profile.data.cv_filename}
                    </span>
                    <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
                      <label className="btn btn-secondary btn-sm" style={{ cursor: "pointer" }}>
                        {uploadCv.isPending ? "Uploading…" : "Replace CV"}
                        <input
                          type="file"
                          accept=".pdf,.docx,.txt,.md"
                          style={{ display: "none" }}
                          disabled={uploadCv.isPending}
                          onChange={(e) => e.target.files?.[0] && uploadCv.mutate(e.target.files[0])}
                        />
                      </label>
                      <button className="btn btn-ghost btn-ghost-sm" onClick={() => setShowExtracted((v) => !v)}>
                        {showExtracted ? "Hide extracted text" : "View extracted text"}
                      </button>
                    </div>
                    {uploadCv.isPending && (
                      <div style={{ display: "flex", alignItems: "center", gap: 8, marginTop: 10 }}>
                        <img
                          src="/graduate-user-icon.png"
                          alt=""
                          className="cv-agent-badge"
                          style={{ width: 20, height: 20, objectFit: "contain", borderRadius: 6, background: "var(--surface)", border: "1px solid var(--border)", padding: 3 }}
                        />
                        <span className="text-12 c-muted">Reading your CV and re-extracting your profile…</span>
                        <span style={{ display: "inline-flex", gap: 3 }}>
                          <span className="chat-dot" />
                          <span className="chat-dot" style={{ animationDelay: "0.15s" }} />
                          <span className="chat-dot" style={{ animationDelay: "0.3s" }} />
                        </span>
                      </div>
                    )}
                    {!uploadCv.isPending && cvNotice && (
                      <p className="text-12 c-success" style={{ marginTop: 8 }}>
                        {cvNotice}
                      </p>
                    )}
                    {showExtracted && (
                      <pre
                        className="surface-2"
                        style={{
                          marginTop: 10,
                          maxHeight: 160,
                          overflowY: "auto",
                          borderRadius: 6,
                          padding: "10px 12px",
                          fontFamily: "var(--font-data)",
                          fontSize: 11,
                          color: "var(--text-faint)",
                          whiteSpace: "pre-wrap",
                        }}
                      >
                        {profile.data.cv_text}
                      </pre>
                    )}
                  </div>
                </div>
              ) : (
                <label
                  className="tr"
                  style={{
                    height: 96,
                    border: "2px dashed var(--border-strong)",
                    borderRadius: 10,
                    display: "flex",
                    flexDirection: "column",
                    alignItems: "center",
                    justifyContent: "center",
                    gap: 6,
                    cursor: "pointer",
                  }}
                >
                  <UploadCloud size={22} className="c-faint" />
                  <span className="text-13 c-muted">Drop your CV or click to browse</span>
                  <input
                    type="file"
                    accept=".pdf,.docx,.txt,.md"
                    style={{ display: "none" }}
                    onChange={(e) => e.target.files?.[0] && uploadCv.mutate(e.target.files[0])}
                  />
                </label>
              )}
            </div>
            <Row label="Account email" description="Used to sign in — not editable here">
              <span className="text-13 c-secondary">{me.data?.email}</span>
            </Row>
            {profile.data && <ContactFieldsEditor profile={profile.data} />}
          </SectionCard>

          {profile.data && (
            <SectionCard title="Research profile" icon={<Sparkles size={15} />}>
              {/* Keyed on cv_sha256 so replacing the CV — which can patch
                  full_name/research_summary/interests server-side — remounts
                  this editor and re-seeds its local state instead of the
                  fields silently keeping their pre-upload values. */}
              <ResearchProfileEditor key={profile.data.cv_sha256 ?? "no-cv"} profile={profile.data} />
            </SectionCard>
          )}

          {profile.data && (
            <SectionCard title="Search constraints" icon={<Filter size={15} />}>
              <ConstraintsEditor profile={profile.data} />
            </SectionCard>
          )}

          <SectionCard title="Scoring" icon={<Target size={15} />}>
            <Row label="Score threshold" description="Minimum score to auto-create an application">
              <input
                className="input"
                type="number"
                style={{ width: 80 }}
                defaultValue={settings.data?.score_threshold ?? 60}
                onBlur={(e) => updateSettings.mutate({ score_threshold: Number(e.target.value) })}
              />
            </Row>
          </SectionCard>

          <SectionCard title="Danger zone" icon={<Trash2 size={15} />} titleColor="var(--urgent)" borderColor="var(--danger-border)">
            <Row label="Delete account" description="Permanently remove your account and all data">
              <button className="btn btn-danger btn-sm" disabled title="Not available yet">
                Delete account
              </button>
            </Row>
          </SectionCard>
        </div>

        <div style={{ width: 280, flexShrink: 0, position: "sticky", top: 80 }}>
          <div className="card" style={{ padding: 20 }}>
            <div className="uppercase-label c-faint" style={{ marginBottom: 4 }}>
              Profile setup
            </div>
            <div style={{ height: 4, background: "var(--border)", borderRadius: 2, margin: "8px 0 14px" }}>
              <div
                style={{
                  height: 4,
                  borderRadius: 2,
                  width: `${(completedCount / completeness.length) * 100}%`,
                  background: completedCount === completeness.length ? "var(--success)" : "var(--primary)",
                  transition: "width 300ms var(--ease)",
                }}
              />
            </div>
            {completeness.map((c) => (
              <ChecklistRow key={c.label} done={c.done} label={c.label} />
            ))}
          </div>

          <div className="card" style={{ padding: 20, marginTop: 16 }}>
            <div className="uppercase-label c-faint" style={{ marginBottom: 8 }}>
              Why this matters
            </div>
            <p className="text-12 c-muted" style={{ lineHeight: 1.6 }}>
              Your research summary and constraints drive every search: the prefilter uses your constraints to
              discard clearly-wrong listings before scoring, and the scorer compares each remaining listing
              against your summary. A vague or empty profile is the most common reason searches come back
              looking generic.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
