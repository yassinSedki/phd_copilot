import { FormEvent, useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "@/api/client";
import type { Profile, ProfileUpdate, Settings as Conf, SettingsUpdate } from "@/api/types";

export default function Settings() {
  const qc = useQueryClient();
  const [savedMsg, setSavedMsg] = useState<string | null>(null);

  const profileQ = useQuery<Profile>({
    queryKey: ["profile"],
    queryFn: () => api.get<Profile>("/profile"),
  });
  const settingsQ = useQuery<Conf>({
    queryKey: ["settings"],
    queryFn: () => api.get<Conf>("/settings"),
  });

  const [profile, setProfile] = useState<ProfileUpdate>({});
  const [conf, setConf] = useState<SettingsUpdate>({ score_threshold: 70 });

  useEffect(() => {
    if (profileQ.data) {
      setProfile({
        full_name: profileQ.data.full_name ?? "",
        research_summary: profileQ.data.research_summary ?? "",
        interests: profileQ.data.interests ?? "",
        languages: profileQ.data.languages ?? "",
        location_prefs: profileQ.data.location_prefs ?? "",
        constraints: profileQ.data.constraints ?? "",
      });
    }
  }, [profileQ.data]);

  useEffect(() => {
    if (settingsQ.data) {
      setConf({
        score_threshold: settingsQ.data.score_threshold,
        scoring_model: settingsQ.data.scoring_model ?? "",
        drafting_model: settingsQ.data.drafting_model ?? "",
        schedule: settingsQ.data.schedule ?? "",
        filters: settingsQ.data.filters ?? {},
      });
    }
  }, [settingsQ.data]);

  const saveProfile = useMutation({
    mutationFn: (body: ProfileUpdate) => api.put<Profile>("/profile", body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["profile"] });
      setSavedMsg("Profile saved.");
      setTimeout(() => setSavedMsg(null), 1500);
    },
  });

  const saveSettings = useMutation({
    mutationFn: (body: SettingsUpdate) => api.put<Conf>("/settings", body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["settings"] });
      setSavedMsg("Settings saved.");
      setTimeout(() => setSavedMsg(null), 1500);
    },
  });

  function submitProfile(e: FormEvent) {
    e.preventDefault();
    saveProfile.mutate(profile);
  }
  function submitSettings(e: FormEvent) {
    e.preventDefault();
    saveSettings.mutate(conf);
  }

  return (
    <div className="space-y-6 max-w-3xl">
      <h1 className="text-2xl font-semibold">Settings</h1>
      {savedMsg && <p className="text-sm text-emerald-600">{savedMsg}</p>}

      <form onSubmit={submitProfile} className="card space-y-4">
        <h2 className="font-medium">Profile</h2>
        <div className="grid md:grid-cols-2 gap-3">
          <div>
            <label className="label">Full name</label>
            <input className="input" value={profile.full_name ?? ""}
              onChange={(e) => setProfile({ ...profile, full_name: e.target.value })} />
          </div>
          <div>
            <label className="label">Languages</label>
            <input className="input" value={profile.languages ?? ""}
              onChange={(e) => setProfile({ ...profile, languages: e.target.value })} />
          </div>
        </div>
        <div>
          <label className="label">Research summary</label>
          <textarea className="input" rows={3} value={profile.research_summary ?? ""}
            onChange={(e) => setProfile({ ...profile, research_summary: e.target.value })} />
        </div>
        <div>
          <label className="label">Interests (keywords)</label>
          <input className="input" value={profile.interests ?? ""}
            onChange={(e) => setProfile({ ...profile, interests: e.target.value })} />
        </div>
        <div className="grid md:grid-cols-2 gap-3">
          <div>
            <label className="label">Location preferences</label>
            <input className="input" value={profile.location_prefs ?? ""}
              onChange={(e) => setProfile({ ...profile, location_prefs: e.target.value })} />
          </div>
          <div>
            <label className="label">Constraints</label>
            <input className="input" value={profile.constraints ?? ""}
              onChange={(e) => setProfile({ ...profile, constraints: e.target.value })} />
          </div>
        </div>
        <div className="flex justify-end">
          <button type="submit" className="btn-primary" disabled={saveProfile.isPending}>
            Save profile
          </button>
        </div>
        {saveProfile.isError && (
          <p className="text-sm text-rose-600">
            {saveProfile.error instanceof ApiError ? saveProfile.error.message : "Failed"}
          </p>
        )}
      </form>

      <form onSubmit={submitSettings} className="card space-y-4">
        <h2 className="font-medium">Scoring & runs</h2>
        <div className="grid md:grid-cols-3 gap-3">
          <div>
            <label className="label">Score threshold</label>
            <input
              type="number"
              min={0}
              max={100}
              className="input"
              value={conf.score_threshold ?? 70}
              onChange={(e) => setConf({ ...conf, score_threshold: Number(e.target.value) })}
            />
            <p className="text-xs text-slate-500 mt-1">Above this auto-creates an application.</p>
          </div>
          <div>
            <label className="label">Scoring model</label>
            <input className="input" value={conf.scoring_model ?? ""}
              onChange={(e) => setConf({ ...conf, scoring_model: e.target.value })} placeholder="claude-haiku-4-5-…" />
          </div>
          <div>
            <label className="label">Drafting model</label>
            <input className="input" value={conf.drafting_model ?? ""}
              onChange={(e) => setConf({ ...conf, drafting_model: e.target.value })} placeholder="claude-sonnet-4-6" />
          </div>
        </div>
        <div>
          <label className="label">Schedule</label>
          <input className="input" value={conf.schedule ?? ""}
            onChange={(e) => setConf({ ...conf, schedule: e.target.value })} placeholder="daily" />
          <p className="text-xs text-slate-500 mt-1">
            Set <code>DAILY_RUN=on</code> in <code>.env</code> to enable the scheduler.
          </p>
        </div>
        <div className="flex justify-end">
          <button type="submit" className="btn-primary" disabled={saveSettings.isPending}>
            Save settings
          </button>
        </div>
      </form>
    </div>
  );
}
