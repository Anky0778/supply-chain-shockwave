import math
from datetime import date

import numpy as np
import pandas as pd


def compute_insights(points: list[tuple[date, float]], unit: str) -> dict:
    if len(points) < 36:
        return {"sufficient_data": False, "reason": "Fewer than 36 monthly observations."}

    s = pd.Series([v for _, v in points], index=pd.to_datetime([d for d, _ in points])).sort_index()
    last_date, last = s.index[-1], float(s.iloc[-1])
    out: dict = {
        "sufficient_data": True,
        "latest": {"date": last_date.date().isoformat(), "value": last, "unit": unit},
        "changes": {},
    }
    notes = [f"Latest monthly average: {last:,.2f} {unit} ({last_date:%B %Y})."]

    for label, n in (("1m", 1), ("12m", 12), ("60m", 60)):
        ref_date = last_date - pd.DateOffset(months=n)
        if ref_date in s.index:
            ref = float(s[ref_date])
            out["changes"][label] = {
                "reference_date": ref_date.date().isoformat(),
                "reference_value": ref,
                "abs": last - ref,
                "pct": (last / ref - 1) * 100,
            }
    if "12m" in out["changes"]:
        c = out["changes"]["12m"]
        direction = "Up" if c["pct"] >= 0 else "Down"
        notes.append(f"{direction} {abs(c['pct']):.1f}% over 12 months "
                     f"(from {c['reference_value']:,.2f} in {c['reference_date'][:7]}).")

    win = s.iloc[-120:]
    pct_rank = float((win <= last).mean() * 100)
    out["percentile_10y"] = {"pct": pct_rank, "months": len(win)}
    notes.append(f"Higher than {pct_rank:.0f}% of monthly values over the last "
                 f"{len(win) / 12:.0f} years.")

    w5 = s.iloc[-60:]
    peak_date, peak = w5.idxmax(), float(w5.max())
    dd = (last / peak - 1) * 100
    out["drawdown_5y"] = {"peak_date": peak_date.date().isoformat(), "peak_value": peak, "pct": dd}
    if dd >= -0.05:
        notes.append("At its highest monthly level in the last 5 years.")
    else:
        notes.append(f"{abs(dd):.1f}% below its {peak_date:%b %Y} high of {peak:,.2f} "
                     "(highest in the last 5 years).")

    if (s > 0).all():
        r = np.log(s).diff().dropna().iloc[-36:]
        vol = float(r.std() * math.sqrt(12) * 100)
        out["volatility_3y"] = {"annualised_pct": vol, "months": len(r)}
        notes.append(f"Annualised volatility over the last {len(r)} months: {vol:.1f}% "
                     "(standard deviation of monthly log changes).")

    out["notes"] = notes
    return out