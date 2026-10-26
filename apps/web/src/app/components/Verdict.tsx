import type { ForecastData } from "./ForecastPanel";

type InsightsLite = {
  percentile_10y?: { pct: number; months: number };
  volatility_3y?: { annualised_pct: number; months: number };
};

const pc = (n: number) => `${n > 0 ? "+" : n < 0 ? "−" : ""}${Math.abs(n).toFixed(0)}%`;

export default function Verdict({
  insights,
  forecast,
}: {
  insights: InsightsLite;
  forecast: ForecastData | null;
}) {
  const p = insights.percentile_10y;
  const v = insights.volatility_3y;
  const h12 = forecast?.horizons?.find((h) => h.horizon_months === 12);
  const anyBeat = forecast?.horizons?.some((h) => h.status === "model_beats_baseline");
  const vs10 = forecast?.context?.price_vs_10y_geometric_mean_pct;

  const level = !p ? null : p.pct >= 80 ? "High" : p.pct <= 20 ? "Low" : "Mid-range";
  const swing = !v ? null : v.annualised_pct < 15 ? "Relatively steady" : v.annualised_pct <= 30 ? "Moderately bumpy" : "Very bumpy";

  const card = "border-t border-ink pt-3";
  return (
    <section className="mt-8">
      <p className="meta">In plain English · computed from the data below</p>
      <div className="mt-3 grid gap-6 md:grid-cols-3">
        <div className={card}>
          <p className="meta">Is it expensive right now?</p>
          <p className="mt-1 font-serif text-2xl">{level ? `${level} compared with history` : "Not enough history"}</p>
          {p && (
            <p className="mt-1 text-sm text-ink-2">
              The latest price is higher than {p.pct.toFixed(0)}% of monthly prices over the last{" "}
              {Math.round(p.months / 12)} years
              {vs10 !== undefined ? `, and ${pc(vs10)} versus the 10-year average` : ""}.
            </p>
          )}
        </div>

        <div className={card}>
          <p className="meta">How bumpy is it?</p>
          <p className="mt-1 font-serif text-2xl">{swing ?? "Not enough history"}</p>
          {v && (
            <p className="mt-1 text-sm text-ink-2">
              In a typical year the price has moved up or down by about {v.annualised_pct.toFixed(0)}%
              (last {Math.round(v.months / 12)} years). Rough guide: under 15% steady, over 30% very bumpy.
            </p>
          )}
        </div>

        <div className={card}>
          <p className="meta">Where could it go next?</p>
          {!forecast || !forecast.supported ? (
            <p className="mt-1 text-sm text-ink-2">No forecast is shown because the data is inadequate.</p>
          ) : anyBeat ? (
            <>
              <p className="mt-1 font-serif text-2xl">A weak signal at some horizons</p>
              <p className="mt-1 text-sm text-ink-2">
                A tested method beat the &ldquo;no change&rdquo; baseline at some horizons. See the forecast section for
                which, and how wide the uncertainty is.
              </p>
            </>
          ) : (
            <>
              <p className="mt-1 font-serif text-2xl">No reliable direction</p>
              <p className="mt-1 text-sm text-ink-2">
                We tested simple forecasting methods on past data and none beat &ldquo;assume no change&rdquo;, so we don&apos;t
                guess a direction.
                {h12 && h12.range_low_pct !== undefined && h12.range_high_pct !== undefined
                  ? ` In recent history, one-year changes have mostly fallen between ${pc(h12.range_low_pct)} and ${pc(h12.range_high_pct)}. That describes the past, not a prediction.`
                  : ""}
              </p>
            </>
          )}
        </div>
      </div>
    </section>
  );
}