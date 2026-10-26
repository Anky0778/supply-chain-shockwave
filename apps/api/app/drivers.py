"""Linked prices: test AI-proposed links against the data, and surface links the AI missed."""
import numpy as np
import pandas as pd

WINDOW = 120   # months of history used
LAGS = range(0, 7)


def _series(points):
    return pd.Series([v for _, v in points],
                     index=pd.to_datetime([d for d, _ in points])).sort_index()


def _best_lag(t_ret, d_ret):
    best = None
    for k in LAGS:
        x = pd.concat([t_ret, d_ret.shift(k)], axis=1).dropna().iloc[-WINDOW:]
        if len(x) < 48:
            continue
        r = float(x.iloc[:, 0].corr(x.iloc[:, 1]))
        if np.isnan(r):
            continue
        if best is None or abs(r) > abs(best["r"]):
            best = {"lag_months": k, "r": r, "n": len(x)}
    return best


def compute_drivers(target: str, cfg: list, series: dict, names: dict,
                    discover: int = 3, min_abs_r: float = 0.2) -> dict:
    """cfg: list of (slug, mechanism, relation, origin) proposed by the AI."""
    if target not in series or len(series[target]) < 60:
        return {"configured": True, "items": [], "reason": "Not enough price history."}

    t_ret = np.log(_series(series[target])).diff()

    def build(slug, mechanism, relation, origin):
        d = _series(series[slug])
        d_ret = np.log(d).diff()
        change = None
        ref = d.index[-1] - pd.DateOffset(months=12)
        if ref in d.index:
            change = float((d.iloc[-1] / d[ref] - 1) * 100)
        return {
            "slug": slug, "name": names.get(slug, slug), "origin": origin,
            "relation": relation, "mechanism": mechanism,
            "driver_change_12m_pct": change,
            "driver_latest_date": d.index[-1].date().isoformat(),
            "link": _best_lag(t_ret, d_ret),
        }

    items, used = [], {target}
    for slug, mechanism, relation, origin in cfg:
        if slug in used or slug not in series or len(series[slug]) < 60:
            continue
        items.append(build(slug, mechanism, relation, origin))
        used.add(slug)
    items.sort(key=lambda i: abs(i["link"]["r"]) if i["link"] else 0, reverse=True)

    found = []
    for slug in series:
        if slug in used or len(series[slug]) < 60:
            continue
        it = build(slug, None, None, "data")
        if it["link"] and abs(it["link"]["r"]) >= min_abs_r:
            found.append(it)
    found.sort(key=lambda i: abs(i["link"]["r"]), reverse=True)

    return {"configured": True, "items": items + found[:discover], "tested_against": len(series) - 1}