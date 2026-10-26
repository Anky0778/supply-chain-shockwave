type Driver = {
  slug: string;
  name: string;
  origin: "ai" | "data";
  relation: string | null;
  mechanism: string | null;
  driver_change_12m_pct: number | null;
  driver_latest_date: string;
  link: { lag_months: number; r: number; n: number } | null;
};
export type DriversData = {
  configured: boolean;
  items: Driver[];
  reason?: string;
  ai_note?: string;
  tested_against?: number;
};

const strength = (r: number) => (Math.abs(r) < 0.15 ? "weak" : Math.abs(r) < 0.3 ? "modest" : "clear");
const REL: Record<string, string> = {
  input_cost: "Input cost", substitute: "Substitute", complement: "Complement", energy: "Energy",
  demand_proxy: "Demand gauge", co_produced: "Produced together", other: "Related",
};

function Card({ d, target }: { d: Driver; target: string }) {
  const ch = d.driver_change_12m_pct;
  const l = d.link;
  return (
    <div className="border-t border-ink pt-3">
      <div className="flex flex-wrap items-baseline gap-2">
        <p className="font-medium">{d.name}</p>
        {d.relation && <span className="meta border border-rule px-2 py-0.5">{REL[d.relation] ?? "Related"}</span>}
      </div>
      <p className="mt-1 text-sm text-ink-2">
        {d.mechanism ?? "No documented mechanism. Statistical association only."}
      </p>
      <p className="mt-2 font-mono text-sm">
        {ch === null ? "12-month change: —" : `${ch >= 0 ? "▲ +" : "▼ −"}${Math.abs(ch).toFixed(1)}% over 12 months`}
      </p>
      {l ? (
        <p className="mt-1 text-sm">
          In the past, {target} price changes tended to move in the {l.r >= 0 ? "same" : "opposite"} direction as{" "}
          {d.name.toLowerCase()} (<strong>{strength(l.r)} link</strong>
          {l.lag_months === 0
            ? ", strongest in the same month"
            : `, strongest about ${l.lag_months} month${l.lag_months > 1 ? "s" : ""} later`}
          ).
        </p>
      ) : (
        <p className="mt-1 text-sm text-ink-2">Not enough overlapping history to measure.</p>
      )}
      <p className="meta mt-1 normal-case">
        {l ? `r = ${l.r.toFixed(2)} · ${l.n} months · ` : ""}latest {d.driver_latest_date.slice(0, 7)}
      </p>
    </div>
  );
}

export default function DriversPanel({ data, targetName }: { data: DriversData | null; targetName: string }) {
  if (!data || !data.configured || data.items.length === 0) return null;
  const target = targetName.toLowerCase();
  const ai = data.items.filter((i) => i.origin === "ai");
  const found = data.items.filter((i) => i.origin === "data");

  return (
    <section className="mt-10 border-t border-ink pt-3">
      <p className="meta">What it moves with · linked prices · measured from the last 10 years</p>
      {data.ai_note && <p className="mt-2 text-sm text-ink-2">{data.ai_note}</p>}

      {ai.length > 0 && (
        <>
          <p className="mt-3 max-w-3xl text-sm text-ink-2">
            <strong>Proposed by AI, then tested on the data.</strong> An AI model suggested these links and the
            economic reason for each. The measured strength below comes from the actual price history, and a
            weak result is shown as weak.
          </p>
          <div className="mt-4 grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            {ai.map((d) => <Card key={d.slug} d={d} target={target} />)}
          </div>
        </>
      )}

      {found.length > 0 && (
        <>
          <p className="mt-8 max-w-3xl text-sm text-ink-2">
            <strong>Also found in the data.</strong> Strongest statistical links among the other{" "}
            {data.tested_against} price series that the AI did not suggest. With this many comparisons, some links
            appear by chance, so treat these as leads, not explanations.
          </p>
          <div className="mt-4 grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            {found.map((d) => <Card key={d.slug} d={d} target={target} />)}
          </div>
        </>
      )}

      <p className="meta mt-4 normal-case">
        Method: correlation of monthly price changes over the last 10 years, best of delays from 0 to 6 months,
        so the strength is slightly flattered. It describes the past and does not prove cause.
      </p>
    </section>
  );
}