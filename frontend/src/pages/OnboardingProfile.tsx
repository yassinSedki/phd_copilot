import { FormEvent, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";
import type { Profile, ProfileUpdate } from "@/api/types";

export default function OnboardingProfile() {
  const navigate = useNavigate();
  const qc = useQueryClient();

  const { data, isLoading } = useQuery<Profile>({
    queryKey: ["profile"],
    queryFn: () => api.get<Profile>("/profile"),
  });

  const [form, setForm] = useState<ProfileUpdate>({
    full_name: "",
    research_summary: "",
    interests: "",
    languages: "",
    location_prefs: "",
    constraints: "",
  });

  useEffect(() => {
    if (data) {
      setForm({
        full_name: data.full_name ?? "",
        research_summary: data.research_summary ?? "",
        interests: data.interests ?? "",
        languages: data.languages ?? "",
        location_prefs: data.location_prefs ?? "",
        constraints: data.constraints ?? "",
      });
    }
  }, [data]);

  const mutation = useMutation({
    mutationFn: (body: ProfileUpdate) => api.put<Profile>("/profile", body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["profile"] });
      navigate("/dashboard");
    },
  });

  function submit(e: FormEvent) {
    e.preventDefault();
    mutation.mutate(form);
  }

  if (isLoading) return <p className="text-slate-500">Loading…</p>;

  return (
    <div className="max-w-2xl space-y-4">
      <h1 className="text-2xl font-semibold">Tell us about your research</h1>
      <p className="text-slate-600 text-sm">
        We use this to score opportunities against your fit. You can refine it later in Settings.
      </p>
      <form onSubmit={submit} className="card space-y-4">
        <div>
          <label className="label">Full name</label>
          <input
            className="input"
            value={form.full_name ?? ""}
            onChange={(e) => setForm({ ...form, full_name: e.target.value })}
          />
        </div>
        <div>
          <label className="label">Research summary</label>
          <textarea
            className="input"
            rows={4}
            placeholder="One paragraph: what you've worked on and what you want to do next."
            value={form.research_summary ?? ""}
            onChange={(e) => setForm({ ...form, research_summary: e.target.value })}
          />
        </div>
        <div>
          <label className="label">Interests (keywords)</label>
          <input
            className="input"
            placeholder="attosecond physics, machine learning, plasma…"
            value={form.interests ?? ""}
            onChange={(e) => setForm({ ...form, interests: e.target.value })}
          />
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="label">Languages</label>
            <input
              className="input"
              value={form.languages ?? ""}
              onChange={(e) => setForm({ ...form, languages: e.target.value })}
            />
          </div>
          <div>
            <label className="label">Location preferences</label>
            <input
              className="input"
              value={form.location_prefs ?? ""}
              onChange={(e) => setForm({ ...form, location_prefs: e.target.value })}
            />
          </div>
        </div>
        <div>
          <label className="label">Constraints (visa, family, etc.)</label>
          <textarea
            className="input"
            rows={2}
            value={form.constraints ?? ""}
            onChange={(e) => setForm({ ...form, constraints: e.target.value })}
          />
        </div>
        {mutation.isError && (
          <p className="text-sm text-rose-600">Save failed. Try again.</p>
        )}
        <div className="flex justify-end">
          <button type="submit" className="btn-primary" disabled={mutation.isPending}>
            {mutation.isPending ? "Saving…" : "Save & continue"}
          </button>
        </div>
      </form>
    </div>
  );
}
