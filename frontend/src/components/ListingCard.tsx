import { Link } from "react-router-dom";
import type { ListingWithScore } from "@/api/types";
import ScoreBadge from "./ScoreBadge";
import DeadlineCountdown from "./DeadlineCountdown";

interface Props {
  listing: ListingWithScore;
}

export default function ListingCard({ listing }: Props) {
  return (
    <Link
      to={`/opportunities/${listing.id}`}
      className="card hover:border-brand-500 hover:shadow transition-all block"
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="font-medium text-slate-900 truncate">
            {listing.title || "Untitled"}
          </div>
          <div className="text-sm text-slate-600 truncate">
            {listing.institution || "—"}
            {listing.country ? ` · ${listing.country}` : ""}
          </div>
          <div className="mt-2 flex items-center gap-3 text-xs text-slate-500">
            {listing.research_field && <span>{listing.research_field}</span>}
            {listing.offer_type && <span className="pill bg-slate-100 text-slate-600">{listing.offer_type}</span>}
            <DeadlineCountdown deadline={listing.deadline} />
          </div>
        </div>
        <ScoreBadge score={listing.latest_score?.score ?? null} />
      </div>
    </Link>
  );
}
