export type ForecastHorizon = {
  horizon_months: number;
  status: "model_beats_baseline" | "no_skill_over_baseline" | "insufficient_data";
  model_used?: string;
  direction?: "up" | "down" | null;
  central_change_pct?: number | null;
  range_low_pct?: number;
  range_high_pct?: number;
  backtest_coverage_80?: number | null;
  best_skill_pct?: number;
  base_rate_up_pct?: number;
  base_rate_windows?: number;
  backtest?: { origins: number; first_origin: string; last_origin: string };
};
export type ForecastData = {
  supported: boolean;
  reason?: string;
  model_version?: string;
  summary?: string;
  reference?: { date: string; value: number; unit: string };
  context?: { price_vs_10y_geometric_mean_pct: number };
  horizons?: ForecastHorizon[];
};

const label = (m: number) => (m < 12 ? `${m} months` : m === 12 ? "1 year" : `${m / 12} years`);
const pc = (n: number, d = 0) => {
  const r = Number(Math.abs(n).toFixed(d));
  return `${r === 0 ? "" : n > 0 ? "+" : "−"}${r.toFixed(d)}%`;
};

export default function ForecastPanel({ data }: { data: ForecastData | null }) {
  if (!data || !data.supported) {
    return (
      <p className="mt-2 text-sm text-ink-2">
        {data?.reason ?? "Forecast unavailable."} No forecast is shown when data is inadequate.
      </p>
    );
  }
  const rows = (data.horizons ?? []).filter((h) => h.status !== "insufficient_data");
  const min = Math.min(0, ...rows.map((h) => h.range_low_pct ?? 0));
  const max = Math.max(0, ...rows.map((h) => h.range_high_pct ?? 0));
  const pos = (v: number) => `${((v - min) / (max - min)) * 100}%`;

  return (
    <div>
      <p className="mt-2 max-w-3xl text-sm">{data.summary}</p>
      <p className="mt-2 max-w-3xl text-sm text-ink-2">
        How to read the cards: each bar shows where the price ended up compared with today (the vertical line) in
        8 out of 10 past cases. A wider bar means more uncertainty. A dot appears only if a tested method showed
        real skill.
      </p>

      <div className="mt-4 grid gap-6 sm:grid-cols-2 lg:grid-cols-4">
        {rows.map((h) => (
          <div key={h.horizon_months} className="border-t border-ink pt-3">
            <p className="meta">In {label(h.horizon_months)}</p>
            <p className="mt-1 font-mono text-xl">
              {pc(h.range_low_pct ?? 0)} to {pc(h.range_high_pct ?? 0)}
            </p>
            <div className="relative mt-2 h-3 bg-paper-2">
              <div
                className="absolute top-0 h-3"
                style={{
                  left: pos(h.range_low_pct ?? 0),
                  width: `calc(${pos(h.range_high_pct ?? 0)} - ${pos(h.range_low_pct ?? 0)})`,
                  background: "#c9c3b3",
                }}
              />
              <div className="absolute -top-0.5 h-4 w-px bg-ink" style={{ left: pos(0) }} />
              {h.status === "model_beats_baseline" && (
                <div
                  className="absolute top-0.5 h-2 w-2 rounded-full"
                  style={{ left: pos(h.central_change_pct ?? 0), background: "#c8412b" }}
                />
              )}
            </div>
            <p className="mt-2 text-sm">
              {h.status === "model_beats_baseline" ? (
                <span className="text-signal">
                  Model leans {h.direction} ({pc(h.central_change_pct ?? 0, 1)})
                </span>
              ) : (
                <span className="text-ink-2">No reliable direction</span>
              )}
            </p>
            <p className="meta mt-1 normal-case">
              Rose in {h.base_rate_up_pct?.toFixed(0)}% of {h.base_rate_windows} past {label(h.horizon_months)} periods
            </p>
          </div>
        ))}
      </div>

      <details className="mt-6 border-t border-rule pt-3">
        <summary className="meta cursor-pointer">How we tested this (for the curious)</summary>
        <div className="mt-3 max-w-3xl space-y-2 text-sm text-ink-2">
          <p>
            For every past month we asked: using only what was known then, what would each method have predicted?
            We then compared the predictions with what actually happened. The &ldquo;baseline&rdquo; method simply assumes
            no change. A method is used only if it beats that baseline by more than 5% overall and in both halves
            of the test period. Otherwise we show the range only.
          </p>
          <p>
            The &ldquo;range held&rdquo; figure checks the ranges themselves: a range built to cover 80% of outcomes should
            have done so in roughly 80% of past tests.
          </p>
        </div>
        <div className="mt-3 overflow-x-auto">
          <table className="w-full min-w-[560px] text-sm">
            <thead className="meta text-left">
              <tr>
                <th className="py-1 font-normal">Horizon</th>
                <th className="font-normal">Best method vs baseline</th>
                <th className="font-normal">Past tests</th>
                <th className="font-normal">Range held</th>
              </tr>
            </thead>
            <tbody className="font-mono">
              {rows.map((h) => (
                <tr key={h.horizon_months} className="border-t border-rule">
                  <td className="py-1 font-sans">{label(h.horizon_months)}</td>
                  <td>{pc(h.best_skill_pct ?? 0)} better</td>
                  <td className="text-ink-2">
                    {h.backtest?.origins} ({h.backtest?.first_origin.slice(0, 7)} to {h.backtest?.last_origin.slice(0, 7)})
                  </td>
                  <td>
                    {h.backtest_coverage_80 != null ? `${(h.backtest_coverage_80 * 100).toFixed(0)}%` : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="meta mt-3 normal-case">
          Model {data.model_version}. Statistical estimates, not financial advice or guaranteed outcomes. A
          negative &ldquo;better&rdquo; value means the method was worse than assuming no change.
        </p>
      </details>
    </div>
  );
}