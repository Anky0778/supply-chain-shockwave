"""Baseline forecasting with chronological (rolling-origin) backtesting."""
import numpy as np
import pandas as pd

MODEL_VERSION = "baselines-v1"
HORIZONS = (6, 12, 36, 60)
GAP_WINDOW = 120       # months in the trailing average used by the mean-reversion model
MIN_TRAIN = 60         # minimum training pairs
SKILL_THRESHOLD = 0.05  # must beat the baseline by >5% in the full test AND in each half
RECENT_ERRORS = 240


def _ols(x, y):
    if len(x) < MIN_TRAIN or np.std(x) == 0:
        return None
    b, a = np.polyfit(x, y, 1)
    return a, b


def _coverage(errs, h):
    """Share of past 10-90% ranges (built only from already-known errors) that held the outcome."""
    hits = n = 0
    for k in range(len(errs)):
        m = k - h + 1
        if m < MIN_TRAIN:
            continue
        lo, hi = np.percentile(errs[:m], [10, 90])
        n += 1
        hits += bool(lo <= errs[k] <= hi)
    return hits / n if n else None


def _run_horizon(logp, gap, dates, h):
    n = len(logp)
    first = h + GAP_WINDOW + MIN_TRAIN
    if n - h - 1 < first + 2 * MIN_TRAIN:
        return None
    r = np.diff(logp, prepend=np.nan)
    y = np.full(n, np.nan)
    y[: n - h] = logp[h:] - logp[: n - h]
    first_valid = GAP_WINDOW - 1

    truth, preds = [], {"naive": [], "drift": [], "meanrev": []}
    for i in range(first, n - h):
        js = np.arange(first_valid, i - h + 1)  # only outcomes already known at origin i
        fit = _ols(gap[js], y[js])
        truth.append(y[i])
        preds["naive"].append(0.0)
        preds["drift"].append(h * np.nanmean(r[i - 59: i + 1]))
        preds["meanrev"].append(fit[0] + fit[1] * gap[i] if fit else 0.0)

    truth = np.array(truth)
    errs = {k: truth - np.array(v) for k, v in preds.items()}
    half = len(truth) // 2

    def skill(k, sl):
        base = np.mean(np.abs(errs["naive"][sl]))
        return float(1 - np.mean(np.abs(errs[k][sl])) / base)

    models = {}
    for k in ("drift", "meanrev"):
        models[k] = {
            "skill": skill(k, slice(None)),
            "skill_first_half": skill(k, slice(0, half)),
            "skill_second_half": skill(k, slice(half, None)),
        }
    qualifying = [k for k, m in models.items()
                  if min(m["skill"], m["skill_first_half"], m["skill_second_half"]) > SKILL_THRESHOLD]
    selected = max(qualifying, key=lambda k: models[k]["skill"]) if qualifying else None
    use = selected or "naive"

    js = np.arange(first_valid, n - h)
    fit = _ols(gap[js], y[js])
    latest = {
        "naive": 0.0,
        "drift": float(h * np.nanmean(r[n - 60: n])),
        "meanrev": float(fit[0] + fit[1] * gap[-1]) if fit else 0.0,
    }
    center = latest[use]
    lo, hi = np.percentile(errs[use][-RECENT_ERRORS:], [10, 90])
    last = float(np.exp(logp[-1]))
    cov = _coverage(errs[use], h)
    valid = y[~np.isnan(y)]

    return {
        "horizon_months": h,
        "status": "model_beats_baseline" if selected else "no_skill_over_baseline",
        "model_used": use,
        "direction": ("up" if center > 0 else "down") if selected else None,
        "central_change_pct": float((np.exp(center) - 1) * 100) if selected else None,
        "range_low": last * float(np.exp(center + lo)),
        "range_high": last * float(np.exp(center + hi)),
        "range_low_pct": float((np.exp(center + lo) - 1) * 100),
        "range_high_pct": float((np.exp(center + hi) - 1) * 100),
        "backtest_coverage_80": cov,
        "best_skill_pct": float(max(m["skill"] for m in models.values()) * 100),
        "backtest": {
            "origins": int(len(truth)),
            "first_origin": dates[first].date().isoformat(),
            "last_origin": dates[n - h - 1].date().isoformat(),
            "models": models,
        },
        "base_rate_up_pct": float((valid > 0).mean() * 100),
        "base_rate_windows": int(len(valid)),
    }


def run_forecasts(points, unit):
    s = pd.Series([v for _, v in points], index=pd.to_datetime([d for d, _ in points])).sort_index()
    if len(s) < 100 or (s <= 0).any():
        return {"supported": False, "reason": "Needs a longer history of positive monthly prices."}
    logp = np.log(s.values)
    gap = (pd.Series(logp).rolling(GAP_WINDOW).mean() - pd.Series(logp)).values

    horizons = []
    for h in HORIZONS:
        res = _run_horizon(logp, gap, s.index, h)
        horizons.append(res or {"horizon_months": h, "status": "insufficient_data"})

    beats = [x["horizon_months"] for x in horizons if x["status"] == "model_beats_baseline"]
    if beats:
        summary = ("A tested model beat the no-change baseline at these horizons (months): "
                   + ", ".join(map(str, beats)) + ". Elsewhere there is no reliable directional signal.")
    else:
        summary = ("No tested method beat a simple \"no change\" forecast, so no direction is shown. "
                   "The ranges show how far this price has typically moved over each horizon.")
    return {
        "supported": True,
        "model_version": MODEL_VERSION,
        "reference": {"date": s.index[-1].date().isoformat(), "value": float(s.iloc[-1]), "unit": unit},
        "context": {"price_vs_10y_geometric_mean_pct": float((np.exp(-gap[-1]) - 1) * 100)},
        "summary": summary,
        "horizons": horizons,
    }