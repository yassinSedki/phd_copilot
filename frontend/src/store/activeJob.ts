import { create } from "zustand";
import type { SearchResultSummary } from "@/api/types";

export interface ActiveJob {
  jobId: number;
  searchRunId: number | null;
  url: string;
}

interface ActiveJobState {
  job: ActiveJob | null;
  /** Outcome of the most recent finished search — shown on the dashboard so
   * the user always sees what their search actually did. */
  lastResult: SearchResultSummary | null;
  setJob: (job: ActiveJob | null) => void;
  setLastResult: (result: SearchResultSummary | null) => void;
}

export const useActiveJobStore = create<ActiveJobState>((set) => ({
  job: null,
  lastResult: null,
  setJob: (job) => set({ job }),
  setLastResult: (lastResult) => set({ lastResult }),
}));
