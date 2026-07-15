import { useState } from "react";
import { api, ApiError } from "@/api/client";
import SegmentedControl from "@/components/ui/SegmentedControl";
import TagInput from "@/components/ui/TagInput";
import Button from "@/components/ui/Button";
import type { ApplicationType, FundingRequired, OnboardingConstraintsBody } from "@/api/types";

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

function Row({ label, hint, tall = false, children }: { label: string; hint?: string; tall?: boolean; children: React.ReactNode }) {
  return (
    <div
      style={{
        display: "flex",
        flexDirection: tall ? "column" : "row",
        alignItems: tall ? "flex-start" : "center",
        minHeight: 56,
        borderBottom: "1px solid var(--border)",
        padding: "12px 0",
        gap: tall ? 8 : 16,
      }}
    >
      <div style={{ flexShrink: 0, width: tall ? "100%" : 180 }}>
        <div className="text-13 fw-500 c-secondary">{label}</div>
        {hint && <div className="text-12 c-faint" style={{ marginTop: 1 }}>{hint}</div>}
      </div>
      <div style={{ flex: 1, width: tall ? "100%" : undefined }}>{children}</div>
    </div>
  );
}

export default function StepPreferences({ geoHints, onDone }: { geoHints: string[]; onDone: () => void }) {
  const [funding, setFunding] = useState<FundingRequired | "">("");
  const [countries, setCountries] = useState<string[]>([]);
  const [month, setMonth] = useState("");
  const [year, setYear] = useState("");
  const [applicationType, setApplicationType] = useState<ApplicationType | "">("");
  const [hardConstraints, setHardConstraints] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function startWindow(): OnboardingConstraintsBody["start_date_window"] {
    if (!month) return "flexible";
    const now = new Date();
    const target = new Date(Number(year) || now.getFullYear(), MONTHS.indexOf(month));
    const monthsAway = (target.getFullYear() - now.getFullYear()) * 12 + (target.getMonth() - now.getMonth());
    if (monthsAway <= 3) return "0-3m";
    if (monthsAway <= 6) return "3-6m";
    if (monthsAway <= 12) return "6-12m";
    return "flexible";
  }

  async function submit() {
    setBusy(true);
    setError(null);
    try {
      await api.post("/onboarding/constraints", {
        funding_required: funding || null,
        countries: countries.length ? countries : null,
        start_date_window: startWindow(),
        application_type: applicationType || null,
        hard_constraints_text: hardConstraints || null,
      });
      await api.post("/onboarding/complete");
      onDone();
    } catch (e) {
      setError(e instanceof ApiError ? e.message : "Could not save your preferences.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <h1 className="text-20 fw-600 c-primary" style={{ marginBottom: 8 }}>
        Your search preferences
      </h1>
      <p className="text-13 c-muted" style={{ marginBottom: 24 }}>
        These filter what we show you. Change them any time in Settings.
      </p>

      <Row label="Funding required?">
        <SegmentedControl
          options={[
            { value: "yes", label: "Yes" },
            { value: "preferred", label: "Ideally" },
            { value: "no", label: "No" },
          ]}
          value={funding || null}
          onChange={setFunding}
        />
      </Row>

      <Row label="Countries open to?">
        <TagInput values={countries} onChange={setCountries} placeholder={geoHints[0] ? `e.g. ${geoHints[0]}` : "+ Add"} />
      </Row>

      <Row label="Target start date">
        <div style={{ display: "flex", gap: 8 }}>
          <select className="input" style={{ width: 110 }} value={month} onChange={(e) => setMonth(e.target.value)}>
            <option value="">Month</option>
            {MONTHS.map((m) => (
              <option key={m} value={m}>
                {m}
              </option>
            ))}
          </select>
          <select className="input" style={{ width: 90 }} value={year} onChange={(e) => setYear(e.target.value)}>
            <option value="">Year</option>
            {[0, 1, 2].map((offset) => {
              const y = new Date().getFullYear() + offset;
              return (
                <option key={y} value={y}>
                  {y}
                </option>
              );
            })}
          </select>
        </div>
      </Row>

      <Row label="Applying for">
        <SegmentedControl
          options={[
            { value: "phd", label: "PhD" },
            { value: "postdoc", label: "Postdoc" },
            { value: "both", label: "Both" },
          ]}
          value={applicationType || null}
          onChange={setApplicationType}
        />
      </Row>

      <Row label="Hard constraints" tall>
        <textarea
          className="input"
          rows={2}
          style={{ width: "100%" }}
          placeholder="Visa, health, partner location, etc."
          value={hardConstraints}
          onChange={(e) => setHardConstraints(e.target.value)}
        />
      </Row>

      {error && (
        <p className="text-12 c-danger" style={{ marginTop: 12 }}>
          {error}
        </p>
      )}

      <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 24 }}>
        <Button variant="primary" loading={busy} onClick={submit}>
          Start searching →
        </Button>
      </div>
    </div>
  );
}
