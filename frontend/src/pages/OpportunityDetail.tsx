import { useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "@/api/client";
import type { ApplicationRead, ListingDetail } from "@/api/types";
import ScoreBadge from "@/components/ScoreBadge";
import DeadlineCountdown from "@/components/DeadlineCountdown";
import FitBreakdownChart from "@/components/FitBreakdownChart";
import RedFlagList from "@/components/RedFlagList";

export default function OpportunityDetail() {
  const { id } = useParams();
  const listingId = Number(id);
  const navigate = useNavigate();
  const qc = useQueryClient();

  const { data, isLoading } = useQuery<ListingDetail>({
    queryKey: ["listing", listingId],
    queryFn: () => api.get<ListingDetail>(`/listings/${listingId}`),
    enabled: !isNaN(listingId),
  });

  const promote = useMutation({
    mutationFn: () => api.post<ApplicationRead>("/applications", { listing_id: listingId, priority: 0 }),
    onSuccess: (app) => {
      qc.invalidateQueries({ queryKey: ["applications"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
      navigate(`/tracker/${app.id}`);
    },
  });

  if (isLoading) return <p className="text-slate-500">Loading…</p>;
  if (!data) return null;

  const score = data.latest_score;

  return (
    <div className="grid md:grid-cols-[2fr_1fr] gap-6">
      <div className="space-y-4">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-semibold">{data.title || "Untitled"}</h1>
            <p className="text-slate-600">
              {data.institution} · {[data.city, data.country].filter(Boolean).join(", ")}
            </p>
            <p className="text-sm text-slate-500 mt-1">
              {data.research_field} · {data.offer_type}
            </p>
          </div>
          <ScoreBadge score={score?.score ?? null} />
        </div>

        <div className="card space-y-3">
          <DeadlineCountdown deadline={data.deadline} />
          {data.funding_info && <p className="text-sm"><b>Funding: </b>{data.funding_info}</p>}
          {data.contact_email && (
            <p className="text-sm">
              <b>Contact: </b>
              <a className="text-brand-600 hover:underline" href={`mailto:${data.contact_email}`}>{data.contact_email}</a>
            </p>
          )}
          {data.application_url && (
            <p className="text-sm">
              <b>Apply: </b>
              <a className="text-brand-600 hover:underline" href={data.application_url} target="_blank" rel="noreferrer">
                {data.application_url}
              </a>
            </p>
          )}
          {data.required_docs && data.required_docs.length > 0 && (
            <div className="text-sm">
              <b>Required documents: </b>{data.required_docs.join(", ")}
            </div>
          )}
        </div>

        {data.description && (
          <div className="card">
            <h3 className="font-medium mb-2">Description</h3>
            <p className="text-sm whitespace-pre-wrap text-slate-700">{data.description}</p>
          </div>
        )}
      </div>

      <aside className="space-y-4">
        <div className="card space-y-3">
          <h3 className="font-medium">Add to tracker</h3>
          <p className="text-sm text-slate-500">
            Promote this listing to your application tracker — you can draft a letter and tick docs from there.
          </p>
          <button
            className="btn-primary w-full"
            disabled={promote.isPending}
            onClick={() => promote.mutate()}
          >
            {promote.isPending ? "Adding…" : "Add to tracker"}
          </button>
          {promote.isError && (
            <p className="text-xs text-rose-600">
              {promote.error instanceof ApiError ? promote.error.message : "Failed"}
            </p>
          )}
        </div>

        <div className="card space-y-3">
          <h3 className="font-medium">Score breakdown</h3>
          <FitBreakdownChart breakdown={score?.fit_breakdown ?? null} />
          {score?.reasons && (
            <p className="text-xs text-slate-500 mt-2">{score.reasons}</p>
          )}
        </div>

        <div className="card">
          <h3 className="font-medium mb-2">Red flags</h3>
          <RedFlagList flags={score?.red_flags ?? null} />
        </div>
      </aside>
    </div>
  );
}
