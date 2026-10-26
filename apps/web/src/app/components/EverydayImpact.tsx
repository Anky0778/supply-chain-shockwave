type Item = {
  ai_rank: number;
  downstream_product: string;
  why: string | null;
  link_type: string | null;
  delay: string | null;
};
export type EverydayData = { model: string | null; generated_at: string | null; items: Item[] };

const LABEL: Record<string, string> = { direct: "Direct", indirect: "Indirect", minor: "Minor" };

export default function EverydayImpact({
  data,
  materialName,
}: {
  data: EverydayData | null;
  materialName: string;
  slug?: string;
}) {
  if (!data || data.items.length === 0) return null;

  return (
    <section className="mt-10 border-t border-ink pt-3">
      <p className="meta">What this touches in everyday life · AI-written background · no figures · unverified</p>
      <p className="mt-2 max-w-3xl text-sm text-ink-2">
        A change in the price of {materialName.toLowerCase()} can reach households through the products below.{" "}
        <strong>Direct</strong> means it is a main ingredient or input. <strong>Indirect</strong> means the effect
        travels through other costs such as feed, fuel or transport. <strong>Minor</strong> means a small effect.
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
      <p className="meta mt-3 normal-case">
        Written by {data.model ?? "an AI model"}
        {data.generated_at ? ` on ${data.generated_at.slice(0, 10)}` : ""} as general background. It states no
        amounts, and it is not checked against sources or used in any calculation.
      </p>
    </section>
  );
}