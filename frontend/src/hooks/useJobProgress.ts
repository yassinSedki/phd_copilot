import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import type { JobRead } from "@/api/types";

export function useJobProgress(jobId: number | null) {
  return useQuery<JobRead>({
    enabled: jobId !== null,
    queryKey: ["job", jobId],
    queryFn: () => api.get<JobRead>(`/jobs/${jobId}`),
    refetchInterval: (q) => {
      const data = q.state.data;
      if (!data) return 800;
      return data.status === "done" || data.status === "failed" ? false : 800;
    },
  });
}
