"use client";

import { useEffect, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type Item = {
  ai_rank: number;
  downstream_product: string;
  why: string | null;
  link_type: string | null;
  delay: string | null;
};
type Impact = {
  status: "ready" | "generating" | "failed" | "busy";
  model?: string | null;
  generated_at?: string | null;
  items: Item[];
};

const LABEL: Record<string, string> = { direct: "Direct", indirect: "Indirect", minor: "Minor" };

export default function EverydayImpactLive({ slug, materialName }: { slug: string; materialName: string }) {
  const [data, setData] = useState<Impact | null>(null);
  const [offline, setOffline] = useState(false);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let cancelled = false;
    let timer: ReturnType<typeof setTimeout> | undefined;
    let tries = 0;

    async function load() {
      try {
        const res = await fetch(`${API}/products/${slug}/impact`, { cache: "no-store" });
        if (!res.ok) throw new Error(String(res.status));
        const j = (await res.json()) as Impact;
        if (cancelled) return;
        setData(j);
        setOffline(false);
        if (j.status === "generating" && tries++ < 40) timer = setTimeout(load, 3000);
      } catch {
        if (cancelled) return;
        setOffline(true); // the server may be waking up: keep trying
        if (tries++ < 40) timer = setTimeout(load, 5000);
      }
    }
    load();
    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [slug, attempt]);

  const head = (
    <div className="flex flex-wrap items-baseline gap-3">
      <p className="meta">What this touches in everyday life</p>
    </div>
  );
  if (!data) {
    return (
      <section className="mt-10 border-t border-ink pt-3">
        {head}
        <p className="mt-2 text-sm text-ink-2">
          {offline ? "Waking up the server, this can take up to a minute. Retrying…" : "Loading…"}
        </p>
      </section>
    );
  }

  if (data.status === "generating") {
    return (
      <section className="mt-10 border-t border-ink pt-3">
        {head}
        <p className="mt-2 text-sm text-ink-2">
          Preparing a background note on how {materialName.toLowerCase()} reaches everyday products. This takes
          roughly 10 to 20 seconds the first time, and it is saved after that.
        </p>
        <div className="mt-4 space-y-3">
          {[0, 1, 2, 3, 4].map((i) => (
            <div key={i} className="h-10 animate-pulse bg-paper-2" />
          ))}
        </div>
      </section>
    );
  }

  if (data.status === "failed" || data.status === "busy") {
    return (
      <section className="mt-10 border-t border-ink pt-3">
        {head}
        <p className="mt-2 text-sm text-ink-2">
          {data.status === "busy"
            ? "Many analyses are being generated right now. Please try again in a few minutes."
            : "This background note could not be prepared just now."}{" "}
          <button type="button" className="underline hover:text-signal" onClick={() => { setData(null); setAttempt((a) => a + 1); }}>
            Try again
          </button>
        </p>
      </section>
    );
  }

  return (
    <section className="mt-10 border-t border-ink pt-3">
      {head}
      <p className="mt-2 max-w-3xl text-sm text-ink-2">
        How a change in the price of {materialName.toLowerCase()} can reach households. <strong>Direct</strong>:
        a main ingredient or input. <strong>Indirect</strong>: the effect travels through other costs such as
        feed, fuel or transport. <strong>Minor</strong>: a small effect.
      </p>
      <ul className="mt-3 divide-y divide-rule">
        {data.items.map((i) => (
          <li key={i.downstream_product} className="grid gap-2 py-3 md:grid-cols-12">
            <div className="md:col-span-3">
              <p className="font-medium">{i.downstream_product}</p>
              <span
                className={`meta mt-1 inline-block border px-2 py-0.5 ${
                  i.link_type === "direct" ? "border-ink bg-ink text-paper" : "border-rule"
                }`}
              >
                {LABEL[i.link_type ?? ""] ?? "Link"}
              </span>
            </div>
            <p className="text-sm text-ink-2 md:col-span-7">{i.why}</p>
            <p className="meta normal-case md:col-span-2">{i.delay ? `Typical delay: ${i.delay}` : ""}</p>
          </li>
        ))}
      </ul>
      <details className="mt-3">
        <summary className="meta cursor-pointer">About this analysis</summary>
        <p className="mt-2 max-w-3xl text-sm text-ink-2">
        Generated automatically from this commodity&apos;s measured price history
          {data.generated_at ? ` (${data.generated_at.slice(0, 10)})` : ""}. It describes how price changes can
          reach everyday products.
        </p>
      </details>
    </section>
  );
}