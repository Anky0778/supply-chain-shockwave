type Row = { iso3: string; name: string; share_pct: number; generation_twh: number; coal_twh: number; year: number };
export type CountryExposureData = {
  configured: boolean;
  title?: string;
  year?: number;
  largest?: Row[];
  dependent?: Row[];
  min_generation_twh_for_dependence_list?: number;
  source_name?: string;
  source_url?: string;
};

const n0 = (n: number) => n.toLocaleString(undefined, { maximumFractionDigits: 0 });

function Bars({ rows, value, label }: { rows: Row[]; value: (r: Row) => number; label: (r: Row) => string }) {
  const max = Math.max(...rows.map(value), 1);
  return (
    <ul className="mt-2 divide-y divide-rule text-sm">
      {rows.map((r) => (
        <li key={r.iso3} className="py-1.5">
          <div className="flex justify-between gap-3">
            <span>{r.name}</span>
            <span className="font-mono text-ink-2">{label(r)}</span>
          </div>
          <div className="mt-1 h-1.5 bg-paper-2">
            <div className="h-1.5 bg-ink" style={{ width: `${(value(r) / max) * 100}%` }} />
          </div>
        </li>
      ))}
    </ul>
  );
}

export default function CountryExposure({ data, materialName }: { data: CountryExposureData | null; materialName: string }) {
  if (!data || !data.configured || !data.largest || data.largest.length === 0) return null;
  const m = materialName.toLowerCase();

  return (
    <section className="mt-10 border-t border-ink pt-3">
      <p className="meta">{data.title} · exposure by country · measured, not a forecast</p>
      <p className="mt-2 max-w-3xl text-sm text-ink-2">
        If the price of {m} rises, countries that burn a lot of it to make electricity face higher generating
        costs. Whether that reaches household bills depends on regulation, subsidies, long-term contracts and
        whether the {m} is imported or mined at home, which this panel does not show.
      </p>
      <div className="mt-4 grid gap-8 md:grid-cols-2">
        <div>
          <p className="meta">Largest coal-fired electricity (data year {data.year})</p>
          <Bars rows={data.largest} value={(r) => r.coal_twh}
            label={(r) => `${n0(r.coal_twh)} TWh · ${r.share_pct.toFixed(0)}% of its power`} />
        </div>
        <div>
          <p className="meta">
            Most dependent on coal (countries generating at least {data.min_generation_twh_for_dependence_list} TWh)
          </p>
          <Bars rows={data.dependent ?? []} value={(r) => r.share_pct}
            label={(r) => `${r.share_pct.toFixed(0)}% of its power`} />
        </div>
      </div>
      <p className="meta mt-3 normal-case">
        Coal-fired TWh = share of electricity from coal × total generation. The 20 TWh cut-off, used only to keep
        very small systems out of the second list, is our choice. Source:{" "}
        <a href={data.source_url} target="_blank" rel="noreferrer" className="underline hover:text-signal">
          {data.source_name}
        </a>
        .
      </p>
    </section>
  );
}