import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { ArrowDown, ArrowUp, Search, X } from "lucide-react";
import { api } from "@/api/client";
import FilterDropdown from "@/components/ui/FilterDropdown";
import OpportunityRow from "./opportunity/OpportunityRow";
import OpportunityDetailPanel from "./opportunity/OpportunityDetailPanel";
import type { ListingRow } from "@/api/types";

type SortField = "score" | "title" | "deadline";

const COLUMNS = 8;

function SkeletonRows() {
  const widths = [34, 220, 48, 90, 110, 60, 56, 70];
  return (
    <>
      {Array.from({ length: 6 }, (_, r) => (
        <tr key={r} style={{ cursor: "default" }}>
          {widths.map((w, c) => (
            <td key={c}>
              <span className="skeleton" style={{ width: w * (0.7 + ((r + c) % 3) * 0.15) }} />
            </td>
          ))}
        </tr>
      ))}
    </>
  );
}

export default function Opportunities() {
  const [query, setQuery] = useState("");
  const [countries, setCountries] = useState<string[]>([]);
  const [fundedOnly, setFundedOnly] = useState(false);
  const [deadlineWithin, setDeadlineWithin] = useState<"all" | "30" | "60">("all");
  const [minScore, setMinScore] = useState(0);
  const [sort, setSort] = useState<{ field: SortField; dir: "asc" | "desc" }>({ field: "score", dir: "desc" });
  const [openId, setOpenId] = useState<number | null>(null);
  // Single source of truth for "this row is being deleted", shared by both
  // the table row's own delete button and the detail panel's — see the long
  // comment on OpportunityRow's onDeleteStart prop for why this can't just
  // live in row-local state.
  const [removedIds, setRemovedIds] = useState<Set<number>>(new Set());
  const hideDeleting = (id: number) => setRemovedIds((prev) => new Set(prev).add(id));
  const unhideDeleting = (id: number) =>
    setRemovedIds((prev) => {
      const next = new Set(prev);
      next.delete(id);
      return next;
    });

  const { data: rawData, isLoading } = useQuery<ListingRow[]>({
    queryKey: ["listings"],
    queryFn: () => api.get<ListingRow[]>("/listings?limit=200"),
  });
  const data = useMemo(() => rawData?.filter((r) => !removedIds.has(r.id)), [rawData, removedIds]);

  const availableCountries = useMemo(
    () => Array.from(new Set((data ?? []).map((r) => r.country).filter(Boolean))) as string[],
    [data]
  );

  const filtered = useMemo(() => {
    let rows = data ?? [];
    if (query.trim()) {
      const q = query.trim().toLowerCase();
      rows = rows.filter(
        (r) =>
          (r.title || "").toLowerCase().includes(q) ||
          (r.institution || "").toLowerCase().includes(q) ||
          (r.country || "").toLowerCase().includes(q)
      );
    }
    if (countries.length) rows = rows.filter((r) => r.country && countries.includes(r.country));
    rows = rows.filter((r) => (r.latest_score?.score ?? 0) >= minScore);
    if (fundedOnly) rows = rows.filter((r) => r.funding_type === "fully_funded");
    if (deadlineWithin !== "all") {
      rows = rows.filter((r) => {
        if (!r.deadline) return false;
        const days = Math.ceil((new Date(r.deadline).getTime() - Date.now()) / 86400000);
        return days <= Number(deadlineWithin);
      });
    }
    return rows;
  }, [data, query, countries, minScore, fundedOnly, deadlineWithin]);

  const sorted = useMemo(() => {
    const rows = [...filtered];
    const mul = sort.dir === "asc" ? 1 : -1;
    rows.sort((a, b) => {
      if (sort.field === "title") return (a.title || "").localeCompare(b.title || "") * mul;
      if (sort.field === "deadline")
        return (new Date(a.deadline || 0).getTime() - new Date(b.deadline || 0).getTime()) * mul;
      return ((a.latest_score?.score ?? -1) - (b.latest_score?.score ?? -1)) * mul;
    });
    return rows;
  }, [filtered, sort]);

  const activeFilterCount = countries.length + (fundedOnly ? 1 : 0) + (deadlineWithin !== "all" ? 1 : 0) + (minScore > 0 ? 1 : 0);

  function cycleSort() {
    setSort((prev) => {
      if (prev.field === "score" && prev.dir === "desc") return { field: "score", dir: "asc" };
      if (prev.field === "score" && prev.dir === "asc") return { field: "deadline", dir: "asc" };
      if (prev.field === "deadline" && prev.dir === "asc") return { field: "deadline", dir: "desc" };
      return { field: "score", dir: "desc" };
    });
  }

  function clearFilters() {
    setCountries([]);
    setFundedOnly(false);
    setDeadlineWithin("all");
    setMinScore(0);
  }

  return (
    <div>
      <h1 className="text-20 fw-600 c-primary" style={{ marginBottom: 16 }}>
        Opportunities
      </h1>

      <div className="table-card">
        <div className="table-toolbar">
        <div style={{ position: "relative", width: 220 }}>
          <Search size={14} className="c-faint" style={{ position: "absolute", left: 9, top: "50%", transform: "translateY(-50%)" }} />
          <input
            className="input"
            style={{ height: 30, paddingLeft: 28, fontSize: 12 }}
            placeholder="Search title, institution…"
            value={query}
            aria-label="Search opportunities"
            onChange={(e) => setQuery(e.target.value)}
          />
        </div>
        <FilterDropdown label="Country" active={countries.length > 0}>
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            {availableCountries.length === 0 && <span className="text-12 c-faint">No data yet</span>}
            {availableCountries.map((c) => (
              <label key={c} className="text-12 c-secondary" style={{ display: "flex", alignItems: "center", gap: 6 }}>
                <input
                  type="checkbox"
                  checked={countries.includes(c)}
                  onChange={(e) => setCountries(e.target.checked ? [...countries, c] : countries.filter((x) => x !== c))}
                />
                {c}
              </label>
            ))}
          </div>
        </FilterDropdown>

        <FilterDropdown label="Funding" active={fundedOnly}>
          <label className="text-12 c-secondary" style={{ display: "flex", alignItems: "center", gap: 6 }}>
            <input type="checkbox" checked={fundedOnly} onChange={(e) => setFundedOnly(e.target.checked)} />
            Funded only
          </label>
        </FilterDropdown>

        <FilterDropdown label="Deadline" active={deadlineWithin !== "all"}>
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            {(["all", "30", "60"] as const).map((v) => (
              <label key={v} className="text-12 c-secondary" style={{ display: "flex", alignItems: "center", gap: 6 }}>
                <input type="radio" checked={deadlineWithin === v} onChange={() => setDeadlineWithin(v)} />
                {v === "all" ? "Any time" : `Within ${v} days`}
              </label>
            ))}
          </div>
        </FilterDropdown>

        <FilterDropdown label="Min score" active={minScore > 0}>
          <div style={{ width: 160 }}>
            <input
              type="range"
              min={0}
              max={100}
              step={5}
              value={minScore}
              aria-label="Minimum fit score"
              onChange={(e) => setMinScore(Number(e.target.value))}
              style={{ width: "100%" }}
            />
            <div className="text-12 c-faint" style={{ textAlign: "center" }}>
              {minScore}
            </div>
          </div>
        </FilterDropdown>

        {activeFilterCount > 0 && (
          <button className="btn-ghost btn-ghost-sm" onClick={clearFilters}>
            <X size={12} /> Clear
          </button>
        )}

        <span className="data text-11 c-faint" style={{ marginLeft: "auto" }}>
          {sorted.length} {sorted.length === 1 ? "result" : "results"}
        </span>
        <button className="btn btn-secondary btn-sm" onClick={cycleSort}>
          {sort.field === "score" ? "Score" : "Deadline"} {sort.dir === "asc" ? <ArrowUp size={13} /> : <ArrowDown size={13} />}
        </button>
        </div>

        <table className="data-table">
          <thead>
            <tr>
              <th style={{ width: 56 }}>Fit</th>
              <th>Position</th>
              <th style={{ width: 76 }}>Type</th>
              <th style={{ width: 110 }}>Location</th>
              <th style={{ width: 100 }}>Deadline</th>
              <th style={{ width: 80 }}>Funding</th>
              <th style={{ width: 110 }}>Status</th>
              <th style={{ width: 48 }} />
            </tr>
          </thead>
          <tbody>
            {isLoading ? (
              <SkeletonRows />
            ) : sorted.length === 0 ? (
              <tr style={{ cursor: "default", height: 200 }}>
                <td colSpan={COLUMNS}>
                  <div style={{ textAlign: "center", padding: "24px 0" }}>
                    <div className="display" style={{ fontSize: "1.35rem", marginBottom: 6 }}>
                      {activeFilterCount > 0 || query ? "Nothing matches" : "Nothing discovered yet"}
                    </div>
                    <p className="text-13 c-muted" style={{ marginBottom: 14 }}>
                      {activeFilterCount > 0 || query
                        ? "Loosen the filters or clear the search to see everything."
                        : "Paste a listings URL on the dashboard and matches will land here."}
                    </p>
                    {activeFilterCount > 0 || query ? (
                      <button
                        className="btn btn-secondary btn-sm"
                        onClick={() => {
                          clearFilters();
                          setQuery("");
                        }}
                      >
                        Clear everything
                      </button>
                    ) : (
                      <Link to="/dashboard" className="btn btn-primary btn-sm" style={{ display: "inline-flex" }}>
                        Start a search
                      </Link>
                    )}
                  </div>
                </td>
              </tr>
            ) : (
              sorted.map((row) => (
                <OpportunityRow
                  key={row.id}
                  row={row}
                  onOpen={() => setOpenId(row.id)}
                  onDeleteStart={hideDeleting}
                  onDeleteError={unhideDeleting}
                />
              ))
            )}
          </tbody>
        </table>
      </div>

      {openId !== null && (
        <OpportunityDetailPanel
          listingId={openId}
          onClose={() => setOpenId(null)}
          onDeleteStart={hideDeleting}
          onDeleteError={unhideDeleting}
        />
      )}
    </div>
  );
}
