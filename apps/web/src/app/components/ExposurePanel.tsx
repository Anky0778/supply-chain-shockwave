"use client";

import { useState } from "react";

type Item = {
  downstream_product: string;
  unit_basis: string;
  kg_per_unit: number;
  material_cost_per_unit_usd: number;
  source_name: string;
  source_url: string;
  reference_year: number | null;
};

const usd = (n: number) =>
  `${n < 0 ? "−" : n > 0 ? "+" : ""}$${Math.abs(n).toLocaleString(undefined, {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;

export default function ExposurePanel({
  items, referenceDate, usdPerKg, formula, assumption,
}: {
  items: Item[]; referenceDate: string; usdPerKg: number; formula: string; assumption: string;
}) {
  const [pct, setPct] = useState(10);
  const rows = [...items].sort(
    (a, b) => Math.abs(b.material_cost_per_unit_usd) - Math.abs(a.material_cost_per_unit_usd)
  );

  return (
    <div>
      <div className="mt-3 flex flex-wrap items-center gap-4">
        <label htmlFor="pct" className="meta">Hypothetical price change (user-defined)</label>
        <input id="pct" type="range" min={-50} max={100} step={5} value={pct}
          onChange={(e) => setPct(Number(e.target.value))} className="w-56 accent-[#c8412b]" />
        <span className="font-mono text-lg">{pct > 0 ? "+" : ""}{pct}%</span>
      </div>
      <p className="meta mt-2">
        Reference price {referenceDate.slice(0, 7)}: ${usdPerKg.toFixed(2)}/kg · {formula}
      </p>

      <div className="mt-3 overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="meta text-left">
            <tr>
              <th className="py-1 font-normal">Product</th>
              <th className="font-normal">Unit</th>
              <th className="font-normal">Material per unit</th>
              <th className="font-normal">Cost change per unit</th>
              <th className="font-normal">Source</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.downstream_product + r.source_url} className="border-t border-rule align-top">
                <td className="py-2 font-medium">{r.downstream_product}</td>
                <td className="text-ink-2">{r.unit_basis}</td>
                <td className="font-mono">{r.kg_per_unit.toLocaleString()} kg</td>
                <td className="font-mono">{usd((r.material_cost_per_unit_usd * pct) / 100)}</td>
                <td>
                  <a href={r.source_url} target="_blank" rel="noreferrer" className="underline hover:text-signal">
                    {r.source_name}{r.reference_year ? ` (${r.reference_year})` : ""}
                  </a>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="meta mt-3 normal-case">{assumption}</p>
    </div>
  );
}