import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { api } from "@/api/client";
import type { ListingWithScore } from "@/api/types";
import ListingCard from "@/components/ListingCard";
import RunPipelineButton from "@/components/RunPipelineButton";

export default function Opportunities() {
  const [country, setCountry] = useState("");
  const [field, setField] = useState("");
  const [minScore, setMinScore] = useState<number | "">("");
  const [sort, setSort] = useState<"score" | "deadline">("score");

  const params = useMemo(() => {
    const qs = new URLSearchParams();
    if (country) qs.set("country", country);
    if (field) qs.set("field", field);
    if (minScore !== "") qs.set("min_score", String(minScore));
    qs.set("sort", sort);
    qs.set("limit", "100");
    return qs.toString();
  }, [country, field, minScore, sort]);

  const { data, isLoading } = useQuery<ListingWithScore[]>({
    queryKey: ["listings", params],
    queryFn: () => api.get<ListingWithScore[]>(`/listings?${params}`),
  });

  return (
    <div className="space-y-4">
      <div className="flex items-end justify-between flex-wrap gap-3">
        <h1 className="text-2xl font-semibold">Opportunities</h1>
        <RunPipelineButton />
      </div>

      <div className="card grid md:grid-cols-4 gap-3">
        <div>
          <label className="label">Country</label>
          <input
            className="input"
            value={country}
            onChange={(e) => setCountry(e.target.value)}
            placeholder="any"
          />
        </div>
        <div>
          <label className="label">Field</label>
          <input
            className="input"
            value={field}
            onChange={(e) => setField(e.target.value)}
            placeholder="any"
          />
        </div>
        <div>
          <label className="label">Min score</label>
          <input
            className="input"
            type="number"
            min={0}
            max={100}
            value={minScore}
            onChange={(e) => setMinScore(e.target.value === "" ? "" : Number(e.target.value))}
            placeholder="0"
          />
        </div>
        <div>
          <label className="label">Sort by</label>
          <select
            className="input"
            value={sort}
            onChange={(e) => setSort(e.target.value as "score" | "deadline")}
          >
            <option value="score">Score (high → low)</option>
            <option value="deadline">Deadline</option>
          </select>
        </div>
      </div>

      {isLoading ? (
        <p className="text-sm text-slate-500">Loading…</p>
      ) : data && data.length > 0 ? (
        <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-3">
          {data.map((l) => (
            <ListingCard key={l.id} listing={l} />
          ))}
        </div>
      ) : (
        <p className="text-sm text-slate-500">No listings match. Try clearing filters or running the pipeline.</p>
      )}
    </div>
  );
}
