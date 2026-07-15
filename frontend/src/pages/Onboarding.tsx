import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Check } from "lucide-react";
import { useAuthStore } from "@/store/auth";
import type { ExtractedProfile } from "@/api/types";
import StepUploadCv from "./onboarding/StepUploadCv";
import StepReviewProfile from "./onboarding/StepReviewProfile";
import StepPreferences from "./onboarding/StepPreferences";

type Step = 0 | 1 | 2;
const LABELS = ["Upload CV", "Review profile", "Preferences"];

export default function Onboarding() {
  const [step, setStep] = useState<Step>(0);
  const [extracted, setExtracted] = useState<ExtractedProfile | null>(null);
  const navigate = useNavigate();
  const setOnboarded = useAuthStore((s) => s.setOnboarded);
  const fillPct = [33, 66, 100][step];

  return (
    <div style={{ minHeight: "100vh", background: "var(--bg)" }}>
      <div style={{ height: 3, background: "var(--border)" }}>
        <div style={{ height: 3, background: "var(--accent)", width: `${fillPct}%`, transition: "width 400ms ease-out" }} />
      </div>

      <div style={{ display: "flex", justifyContent: "center", marginTop: 32 }}>
        <div style={{ display: "flex", alignItems: "center", width: 320 }}>
          {LABELS.map((label, i) => (
            <div key={label} style={{ display: "flex", alignItems: "center", flex: i < LABELS.length - 1 ? 1 : "0 0 auto" }}>
              <div style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 6 }}>
                <div
                  style={{
                    width: 8,
                    height: 8,
                    borderRadius: "50%",
                    background: i < step ? "var(--accent)" : i === step ? "#fff" : "var(--border-strong)",
                    border: i === step ? "2px solid var(--accent)" : "none",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                  }}
                >
                  {i < step && <Check size={8} color="#fff" strokeWidth={3} />}
                </div>
                <span className="text-11 c-faint" style={{ whiteSpace: "nowrap" }}>
                  {label}
                </span>
              </div>
              {i < LABELS.length - 1 && <div style={{ flex: 1, height: 1, background: "var(--border)", margin: "0 8px 18px" }} />}
            </div>
          ))}
        </div>
      </div>

      <div style={{ maxWidth: 480, margin: "40px auto 0", paddingBottom: 80 }}>
        {step === 0 && (
          <StepUploadCv
            onDone={(e) => {
              setExtracted(e);
              setStep(1);
            }}
          />
        )}
        {step === 1 && <StepReviewProfile initial={extracted} onDone={() => setStep(2)} />}
        {step === 2 && (
          <StepPreferences
            geoHints={extracted?.geographic_hints ?? []}
            onDone={() => {
              setOnboarded(true);
              navigate("/dashboard", { replace: true });
            }}
          />
        )}
      </div>
    </div>
  );
}
