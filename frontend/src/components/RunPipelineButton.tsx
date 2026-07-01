import { useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "@/api/client";
import type { RunResponse } from "@/api/types";
import JobProgressBar from "./JobProgressBar";

export default function RunPipelineButton() {
  const [jobId, setJobId] = useState<number | null>(null);
  const qc = useQueryClient();

  const mutation = useMutation({
    mutationFn: () => api.post<RunResponse>("/runs"),
    onSuccess: (data) => setJobId(data.job_id),
  });

  return (
    <div className="space-y-2">
      <button
        className="btn-primary"
        disabled={mutation.isPending}
        onClick={() => mutation.mutate()}
      >
        {mutation.isPending ? "Starting…" : "Run pipeline"}
      </button>
      <JobProgressBar
        jobId={jobId}
        label="Pipeline (ingest → parse → score)"
        onDone={() => {
          qc.invalidateQueries({ queryKey: ["listings"] });
          qc.invalidateQueries({ queryKey: ["applications"] });
          qc.invalidateQueries({ queryKey: ["dashboard"] });
        }}
      />
    </div>
  );
}
