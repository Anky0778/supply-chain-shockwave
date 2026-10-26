"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import Sparkline from "./Sparkline";

export type OverviewItem = {
  slug: string;
  name: string;
  category: string;
  unit: string | null;
  latest_date: string;
  latest_value: number;
  change_12m_pct: number | null;
  percentile_10y: number | null;
  sparkline: number[];
};
export type TradeOnly = { slug: string; name: string; category: string; hs_code: string | null };

const level = (p: number | null) =>
  p === null ? "—" : p >= 80 ? "High" : p <= 20 ? "Low" : "Mid-range";
const money = (n: number) =>
  n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });

export default function Catalogue({ items, tradeOnly }: { items: OverviewItem[]; tradeOnly: TradeOnly[] }) {
  const [q, setQ] = useState("");
  const [cat, setCat] = useState("All");
  const [sort, setSort] = useState("name");

  const cats = useMemo(
    () => ["All", ...Array.from(new Set(items.map((i) => i.category))).sort()],
    [items]
  );

  const rows = useMemo(() => {
    const term = q.trim().toLowerCase();
    const s = items.filter(
      (i) => (cat === "All" || i.category === cat) && i.name.toLowerCase().includes(term)
    );
    if (sort === "rise") s.sort((a, b) => (b.change_12m_pct ?? -1e9) - (a.change_12m_pct ?? -1e9));
    else if (sort === "fall") s.sort((a, b) => (a.change_12m_pct ?? 1e9) - (b.change_12m_pct ?? 1e9));
    else if (sort === "level") s.sort((a, b) => (b.percentile_10y ?? -1) - (a.percentile_10y ?? -1));
    else s.sort((a, b) => a.name.localeCompare(b.name));
    return s;
  }, [items, q, cat, sort]);

  const field = "border border-rule bg-paper px-2 py-1 text-sm";

  return (
    <div>
      <div className="flex flex-wrap items-center gap-3">
        <input
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Search commodities"
          aria-label="Search commodities"
          className={`${field} w-56`}
        />
        <select value={cat} onChange={(e) => setCat(e.target.value)} className={field} aria-label="Category">
          {cats.map((c) => (
            <option key={c}>{c}</option>
          ))}
        </select>
        <select value={sort} onChange={(e) => setSort(e.target.value)} className={field} aria-label="Sort">
          <option value="name">Sort: name</option>
          <option value="rise">Sort: biggest rise (12 months)</option>
          <option value="fall">Sort: biggest fall (12 months)</option>
          <option value="level">Sort: highest vs history</option>
        </select>
        <span className="meta">{rows.length} shown</span>
      </div>

      <div className="mt-4 overflow-x-auto">
        <table className="w-full min-w-[720px] border-t border-ink text-sm">
          <thead className="meta text-left">
            <tr>
              <th className="py-2 font-normal">Commodity</th>
              <th className="font-normal">5-year trend</th>
              <th className="font-normal">Latest price</th>
              <th className="font-normal">Change, 12 months</th>
              <th className="font-normal">Price vs last 10 years</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.slug} className="border-t border-rule">
                <td className="py-2">
                  <Link href={`/products/${r.slug}`} className="font-medium hover:text-signal">
                    {r.name}
                  </Link>
                  <p className="meta normal-case">{r.category}</p>
                </td>
                <td>
                  <Sparkline values={r.sparkline} />
                </td>
                <td className="font-mono">
                  {money(r.latest_value)} <span className="text-ink-2">{r.unit}</span>
                </td>
                <td
                  className="font-mono"
                  style={
                    r.change_12m_pct !== null && Math.abs(r.change_12m_pct) >= 25
                      ? { color: "var(--color-signal)" }
                      : undefined
                  }
                >
                  {r.change_12m_pct === null
                    ? "—"
                    : `${r.change_12m_pct >= 0 ? "▲ +" : "▼ −"}${Math.abs(r.change_12m_pct).toFixed(1)}%`}
                </td>
                <td>
                  {level(r.percentile_10y)}
                  {r.percentile_10y !== null && (
                    <span className="meta ml-2 normal-case">
                      higher than {r.percentile_10y.toFixed(0)}% of months
                    </span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {tradeOnly.length > 0 && (
        <div className="mt-8 border-t border-rule pt-3">
          <p className="meta">Tracked through trade data only · no price history yet</p>
          <p className="mt-2 text-sm text-ink-2">
            {tradeOnly.map((t, i) => (
              <span key={t.slug}>
                {i > 0 && " · "}
                <Link href={`/products/${t.slug}`} className="hover:text-signal">
                  {t.name}
                </Link>
              </span>
            ))}
          </p>
        </div>
      )}
    </div>
  );
}