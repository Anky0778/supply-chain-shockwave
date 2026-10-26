export default function Methodology() {
  const h = "mt-8 border-t border-ink pt-3 font-serif text-2xl tracking-tight";
  const p = "mt-2 max-w-3xl text-sm text-ink-2";
  return (
    <article>
      <p className="meta">Methodology and sources</p>
      <h1 className="font-serif text-4xl tracking-tight">How to read this site</h1>

      <h2 className={h}>Where the prices come from</h2>
      <p className={p}>
        Prices come from the World Bank&apos;s Commodity Price Data (the &ldquo;Pink Sheet&rdquo;): monthly averages in
        nominal US dollars, back to 1960 for the longest series. This is monthly data published with a delay, not
        a live market feed, and the site never labels it as live. Prices are benchmark averages, not what any
        particular company pays.
      </p>

      <h2 className={h}>What is computed from them</h2>
      <p className={p}>
        Percentage changes compare the latest month with a stated earlier month. &ldquo;Compared with history&rdquo; is the
        share of the last 10 years&apos; monthly prices that were lower than today&apos;s. &ldquo;Bumpiness&rdquo; is the
        annualised standard deviation of monthly log price changes over the last 3 years.
      </p>

      <h2 className={h}>Linked prices</h2>
      <p className={p}>
        For each commodity we list other prices that plausibly influence it, such as fertiliser, oil, gas or a
        substitute crop. The reason for each link is general economic reasoning. We then measure how closely the
        two have moved together over the last 10 years, and after what delay. This describes the past. It shows
        association, not proof of cause.
      </p>

      <h2 className={h}>How forecasts are tested</h2>
      <p className={p}>
        Each method is replayed through history: at every past month it sees only the data available then, makes a
        prediction, and is scored against what happened. The baseline assumes no change. A direction is shown only
        if a method beats the baseline by more than 5% overall and in both halves of the test. Otherwise the site
        shows only the historical range and says there is no reliable direction. Ranges come from past errors, and
        we report how often they held. Statistical forecasts cannot anticipate unannounced shocks such as a sudden
        export ban or a war, which is why current evidence is shown beside them.
      </p>

      <h2 className={h}>Written background notes</h2>
      <p className={p}>
        The notes on how a commodity reaches everyday products are generated automatically by a language model from
        the commodity&apos;s measured price history Quantities used in &ldquo;Products affected&rdquo; come only from sources linked beside each
        row.
      </p>

      <h2 className={h}>Limits</h2>
      <p className={p}>
        Nothing here is financial advice or a guaranteed outcome. Scenario sliders show hypothetical arithmetic,
        not predictions.
      </p>
    </article>
  );
}