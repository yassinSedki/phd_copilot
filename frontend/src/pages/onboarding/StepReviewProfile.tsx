import { useEffect, useRef, useState } from "react";
import { api, ApiError } from "@/api/client";
import TagInput from "@/components/ui/TagInput";
import SegmentedControl from "@/components/ui/SegmentedControl";
import Button from "@/components/ui/Button";
import type { ExtractedProfile } from "@/api/types";

const CAREER_STAGES = [
  { value: "msc", label: "MSc student" },
  { value: "phd", label: "PhD candidate" },
  { value: "other", label: "Other" },
];

function summarize(areas: string[], degree: string | null): string {
  if (!areas.length && !degree) return "";
  const a = areas.slice(0, 3).join(", ");
  if (degree && a) return `Background in ${degree}, focused on ${a}.`;
  return a ? `Focused on ${a}.` : `Background in ${degree}.`;
}

export default function StepReviewProfile({ initial, onDone }: { initial: ExtractedProfile | null; onDone: () => void }) {
  const [fullName, setFullName] = useState(initial?.full_name ?? "");
  const [email, setEmail] = useState(initial?.email ?? "");
  const [phone, setPhone] = useState(initial?.phone ?? "");
  // Prefer the LLM's own multi-sentence summary (grounded in the full CV)
  // — the templated one-liner is only a fallback for the offline stub
  // provider, which can't generate real prose.
  const [summary, setSummary] = useState(
    initial?.research_summary || summarize(initial?.research_areas ?? [], initial?.degree_subject ?? null)
  );
  const [areas, setAreas] = useState<string[]>(initial?.research_areas ?? []);
  const [methods, setMethods] = useState<string[]>(initial?.methods ?? []);
  const [languages, setLanguages] = useState<string[]>(initial?.programming_languages ?? []);
  const [degreeSubject, setDegreeSubject] = useState(initial?.degree_subject ?? "");
  const [gradYear, setGradYear] = useState(initial?.graduation_year?.toString() ?? "");
  const [careerStage, setCareerStage] = useState(initial?.career_stage === "phd_student" ? "phd" : initial?.career_stage || "");
  const [spokenLanguages, setSpokenLanguages] = useState<string[]>(initial?.languages_spoken ?? []);
  const [publications, setPublications] = useState((initial?.publications ?? []).length);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const saveTimer = useRef<ReturnType<typeof setTimeout>>();

  function touch() {
    clearTimeout(saveTimer.current);
    setSaved(false);
    saveTimer.current = setTimeout(() => {
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    }, 800);
  }
  useEffect(() => () => clearTimeout(saveTimer.current), []);

  async function submit() {
    setBusy(true);
    setError(null);
    try {
      await api.post("/onboarding/profile", {
        full_name: fullName || null,
        contact_email: email || null,
        phone: phone || null,
        research_summary: summary || null,
        interests: areas.join(", ") || null,
        skills: methods.length ? methods : null,
        languages: spokenLanguages.join(", ") || null,
        education: [{ subject: degreeSubject || null, graduation_year: gradYear ? Number(gradYear) : null, career_stage: careerStage || null }],
      });
      onDone();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not save your profile.");
    } finally {
      setBusy(false);
    }
  }

  const Field = ({ label, children }: { label: string; children: React.ReactNode }) => (
    <div>
      <label className="text-11 fw-500 c-faint uppercase-label" style={{ display: "block", marginBottom: 8 }}>
        {label}
      </label>
      {children}
    </div>
  );

  return (
    <div style={{ position: "relative" }}>
      <h1 className="text-20 fw-600 c-primary" style={{ marginBottom: 8 }}>
        Does this look right?
      </h1>
      <p className="text-13 c-muted" style={{ marginBottom: 8 }}>
        We extracted this from your CV. Click anything to edit.
      </p>
      <div className="text-11 c-faint" style={{ position: "absolute", top: 0, right: 0, opacity: saved ? 1 : 0 }}>
        Saved
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 20, marginTop: 24 }}>
        <Field label="Full name">
          <input className="input" value={fullName} onChange={(e) => { setFullName(e.target.value); touch(); }} />
        </Field>

        <div style={{ display: "flex", gap: 12 }}>
          <div style={{ flex: 1 }}>
            <Field label="Email">
              <input className="input" type="email" value={email} onChange={(e) => { setEmail(e.target.value); touch(); }} />
            </Field>
          </div>
          <div style={{ flex: 1 }}>
            <Field label="Phone">
              <input className="input" value={phone} onChange={(e) => { setPhone(e.target.value); touch(); }} />
            </Field>
          </div>
        </div>

        <Field label="Research summary">
          <textarea
            className="input"
            rows={7}
            style={{ lineHeight: 1.6, resize: "vertical" }}
            value={summary}
            onChange={(e) => { setSummary(e.target.value); touch(); }}
          />
        </Field>

        <Field label="Research areas">
          <TagInput values={areas} onChange={(v) => { setAreas(v); touch(); }} />
        </Field>

        <Field label="Methods & tools">
          <TagInput values={methods} onChange={(v) => { setMethods(v); touch(); }} />
        </Field>

        <Field label="Programming languages">
          <TagInput values={languages} onChange={(v) => { setLanguages(v); touch(); }} />
        </Field>

        <div style={{ display: "flex", gap: 12 }}>
          <div style={{ flex: 1 }}>
            <Field label="Degree subject">
              <input className="input" value={degreeSubject} onChange={(e) => { setDegreeSubject(e.target.value); touch(); }} />
            </Field>
          </div>
          <div style={{ width: 100 }}>
            <Field label="Grad. year">
              <input className="input" type="number" value={gradYear} onChange={(e) => { setGradYear(e.target.value); touch(); }} />
            </Field>
          </div>
        </div>

        <Field label="Career stage">
          <SegmentedControl options={CAREER_STAGES} value={careerStage || null} onChange={(v) => { setCareerStage(v); touch(); }} />
        </Field>

        <Field label="Languages spoken">
          <TagInput values={spokenLanguages} onChange={(v) => { setSpokenLanguages(v); touch(); }} />
        </Field>

        <Field label="Publications">
          <input
            className="input"
            type="number"
            style={{ width: 80 }}
            value={publications}
            onChange={(e) => { setPublications(Number(e.target.value)); touch(); }}
          />
        </Field>
      </div>

      {error && (
        <p className="text-12 c-danger" style={{ marginTop: 12 }}>
          {error}
        </p>
      )}

      <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 24 }}>
        <Button variant="primary" loading={busy} onClick={submit}>
          Looks good →
        </Button>
      </div>
    </div>
  );
}
