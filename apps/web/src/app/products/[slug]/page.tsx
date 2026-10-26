import Link from "next/link";
import { notFound } from "next/navigation";
import PriceChart from "../../components/PriceChart";
import ExposurePanel from "../../components/ExposurePanel";
import ForecastPanel, { type ForecastData } from "../../components/ForecastPanel";
import Verdict from "../../components/Verdict";
import EverydayImpactLive from "../../components/EverydayImpactLive";
import DriversPanel, { type DriversData } from "../../components/DriversPanel";
import CountryExposure, { type CountryExposureData } from "../../components/CountryExposure";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type Product = {
  slug: string; name: string; category: string; hs_code: string | null;
  price_unit: string | null; has_price_series: boolean;
};
type Prices = { unit: string; basis: string; source: string; points: { date: string; value: number }[] };
type Change = { reference_date: string; reference_value: number; abs: number; pct: number };
type Insights = {
  sufficient_data: boolean;
  latest?: { date: string; value: number; unit: string };
  changes?: Record<string, Change>;
  percentile_10y?: { pct: number; months: number };
  drawdown_5y?: { peak_date: string; peak_value: number; pct: number };
  volatility_3y?: { annualised_pct: number; months: number };
  notes?: string[];
};
type Dependency = {
  downstream_name: string; kind: string; share_pct: number | null; geography: string;
  reference_label: string; source_name: string; source_url: string; confidence: string; note: string | null;
};
type Exposure = {
  reference_price: { date: string; usd_per_kg: number };
  formula: string;
  assumption: string;
  items: {
    downstream_product: string; unit_basis: string; kg_per_unit: number;
    material_cost_per_unit_usd: number; source_name: string; source_url: string;
    reference_year: number | null;
  }[];
};

async function getJson<T>(path: string): Promise<T | null> {
  try {
    const res = await fetch(`${API}${path}`, { cache: "no-store" });
    return res.ok ? ((await res.json()) as T) : null;
  } catch {
    return null;
  }
}

const fmt = (n: number, d = 2) =>
  n.toLocaleString(undefined, { minimumFractionDigits: d, maximumFractionDigits: d });
const sign = (n: number) => (n > 0 ? "+" : "");

export default async function ProductPage({ params }: { params: Promise<{ slug: string }> }) {
  const { slug } = await params;
  const product = await getJson<Product>(`/products/${slug}`);
  if (!product) notFound();

  const [prices, insights, deps, exposure, forecast, drivers, countryExposure] = await Promise.all([
    product.has_price_series ? getJson<Prices>(`/products/${slug}/prices`) : null,
    product.has_price_series ? getJson<Insights>(`/products/${slug}/insights`) : null,
    getJson<Dependency[]>(`/products/${slug}/dependencies`),
    product.has_price_series ? getJson<Exposure>(`/products/${slug}/exposure?price_change_pct=0`) : null,
    product.has_price_series ? getJson<ForecastData>(`/products/${slug}/forecast`) : null,
    product.has_price_series ? getJson<DriversData>(`/products/${slug}/drivers`) : null,
    getJson<CountryExposureData>(`/products/${slug}/country-exposure`),
  ]);

  const ins = insights?.sufficient_data ? insights : null;
  const latest = ins?.latest;
  const priced = !!prices && prices.points.length > 0 && !!ins && !!latest;

  const hasExposure = !!exposure && exposure.items.length > 0;
  const hasDeps = !!deps && deps.length > 0;

  return (
    <article>
      <Link href="/" className="meta hover:text-ink">← Overview</Link>
      <p className="meta mt-4">{product.category} · HS {product.hs_code ?? "n/a"}</p>
      <h1 className="font-serif text-4xl tracking-tight">{product.name}</h1>

      {priced && ins && latest && prices ? (
        <>
          <Verdict insights={ins} forecast={forecast} />

          <div className="mt-10 grid gap-8 lg:grid-cols-3">
            <div className="lg:col-span-2">
              <p className="meta">Latest monthly average · {latest.date.slice(0, 7)}</p>
              <p className="font-mono text-4xl">
                {fmt(latest.value)} <span className="text-base text-ink-2">{latest.unit}</span>
              </p>
              <div className="mt-6">
                <PriceChart points={prices.points} unit={prices.unit} />
              </div>
            </div>

            <aside className="border-t border-ink lg:border-l lg:border-t-0 lg:pl-6">
              <p className="meta mt-3 lg:mt-0">Measured · computed from stored prices</p>
              <table className="mt-3 w-full text-sm">
                <thead className="meta text-left">
                  <tr>
                    <th className="font-normal">Change</th>
                    <th className="font-normal">%</th>
                    <th className="font-normal">Since</th>
                  </tr>
                </thead>
                <tbody className="font-mono">
                  {[["1 month", "1m"], ["12 months", "12m"], ["5 years", "60m"]].map(([label, k]) => {
                    const c = ins.changes?.[k];
                    return (
                      <tr key={k} className="border-t border-rule">
                        <td className="py-1 font-sans">{label}</td>
                        <td>{c ? `${sign(c.pct)}${fmt(c.pct, 1)}%` : "—"}</td>
                        <td className="text-ink-2">{c ? c.reference_date.slice(0, 7) : "—"}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
              <ul className="mt-5 space-y-2 text-sm">
                {ins.notes?.map((n) => (
                  <li key={n} className="border-t border-rule pt-2">{n}</li>
                ))}
              </ul>
            </aside>
          </div>
        </>
      ) : (
        <p className="mt-6 border border-rule p-4 text-sm">
          No price series is available for this product. It is tracked through trade data only, so no
          price chart or forecast is shown.
        </p>
      )}

      <EverydayImpactLive slug={product.slug} materialName={product.name} />

      {priced && <DriversPanel data={drivers} targetName={product.name} />}

      <CountryExposure data={countryExposure} materialName={product.name} />

      {priced && (
        <section className="mt-10 border-t border-ink pt-3">
          <p className="meta">Forecast · model estimate, not measured fact</p>
          <ForecastPanel data={forecast} />
        </section>
      )}

      {hasExposure && exposure && (
        <section className="mt-10 border-t border-ink pt-3">
          <p className="meta">Products affected · verified material content · scenario, not forecast</p>
          <ExposurePanel
            items={exposure.items}
            referenceDate={exposure.reference_price.date}
            usdPerKg={exposure.reference_price.usd_per_kg}
            formula={exposure.formula}
            assumption={exposure.assumption}
          />
        </section>
      )}

      {hasDeps && deps && (
        <section className="mt-10 border-t border-ink pt-3">
          <p className="meta">Where this material is used · documented demand sectors</p>
          <div className="overflow-x-auto">
            <table className="mt-3 w-full text-sm">
              <thead className="meta text-left">
                <tr>
                  <th className="py-1 font-normal">Sector or product</th>
                  <th className="font-normal">Share</th>
                  <th className="font-normal">Scope</th>
                  <th className="font-normal">Source</th>
                </tr>
              </thead>
              <tbody>
                {deps.map((d) => (
                  <tr key={d.downstream_name + d.geography} className="border-t border-rule align-top">
                    <td className="py-2 font-medium">{d.downstream_name}</td>
                    <td className="w-48 pr-4">
                      {d.share_pct === null ? (
                        <span className="font-mono text-ink-2">not recorded</span>
                      ) : (
                        <div className="flex items-center gap-2">
                          <div className="h-2 flex-1 bg-paper-2">
                            <div className="h-2 bg-ink" style={{ width: `${d.share_pct}%` }} />
                          </div>
                          <span className="font-mono">{fmt(d.share_pct, 0)}%</span>
                        </div>
                      )}
                    </td>
                    <td className="text-ink-2">{d.geography}</td>
                    <td>
                      <a href={d.source_url} target="_blank" rel="noreferrer" className="underline hover:text-signal">
                        {d.reference_label}
                      </a>
                      {d.note && <p className="meta mt-1 normal-case">{d.note}</p>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {priced && prices && latest && (
        <p className="mt-10 border-t border-rule pt-3 text-xs text-ink-2">
          Source: {prices.source}. {prices.basis}, {prices.unit}. Monthly data, latest {latest.date.slice(0, 7)};
          not live prices.
        </p>
      )}
    </article>
  );
}