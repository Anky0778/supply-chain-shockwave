"""Load a country-level metric from an Our World in Data grapher CSV.

Usage (from apps/api):
    python -m app.ingest.owid_metric --all
    python -m app.ingest.owid_metric electricity_share_coal
    python -m app.ingest.owid_metric electricity_share_coal path\\to\\downloaded.csv   (offline fallback)
"""
import io
import sys

import httpx
import pandas as pd
from sqlalchemy.dialects.postgresql import insert

from ..db import SessionLocal
from ..models import CountryMetric

Q = "?v=1&csvType=full&useColumnShortNames=false"
METRICS = {
    "electricity_share_coal": {
        "url": "https://ourworldindata.org/grapher/share-electricity-coal.csv" + Q,
        "page": "https://ourworldindata.org/grapher/share-electricity-coal",
        "unit": "% of electricity",
        "source": "Ember (2026); Energy Institute, Statistical Review of World Energy (2025), via Our World in Data",
    },
    "electricity_generation": {
        "url": "https://ourworldindata.org/grapher/electricity-generation.csv" + Q,
        "page": "https://ourworldindata.org/grapher/electricity-generation",
        "unit": "TWh",
        "source": "Ember (2026); Energy Institute, Statistical Review of World Energy (2025), via Our World in Data",
    },
}


def load(metric: str, local_path: str | None = None) -> int:
    cfg = METRICS[metric]
    if local_path:
        df = pd.read_csv(local_path)
    else:
        r = httpx.get(cfg["url"], headers={"User-Agent": "Our World In Data data fetch/1.0"},
                      timeout=90, follow_redirects=True)
        r.raise_for_status()
        df = pd.read_csv(io.StringIO(r.text))

    entity, code, year, value = df.columns[:4]
    df = df[df[code].notna()]
    df = df[df[code].astype(str).str.len() == 3]          # real countries only, no regions/aggregates
    df = df[~df[code].astype(str).str.startswith("OWID")]
    df = df.assign(_v=pd.to_numeric(df[value], errors="coerce")).dropna(subset=["_v"])

    rows = [dict(metric=metric, iso3=str(c), country_name=str(n)[:120], year=int(y), value=float(v),
                 unit=cfg["unit"], source_name=cfg["source"], source_url=cfg["page"])
            for n, c, y, v in zip(df[entity], df[code], df[year], df["_v"])]

    with SessionLocal() as db:
        for k in range(0, len(rows), 2000):
            stmt = insert(CountryMetric).values(rows[k:k + 2000])
            stmt = stmt.on_conflict_do_update(
                constraint="uq_country_metric",
                set_={"value": stmt.excluded.value, "unit": stmt.excluded.unit,
                      "country_name": stmt.excluded.country_name},
            )
            db.execute(stmt)
        db.commit()

    top = df.sort_values("_v", ascending=False).head(3)
    print(f"{metric}: {len(rows)} rows, years {int(df[year].min())}-{int(df[year].max())}. "
          f"Sanity check, largest values: "
          + ", ".join(f"{a} {b:.1f}" for a, b in zip(top[entity], top["_v"])))
    return len(rows)


def main():
    if len(sys.argv) < 2:
        raise SystemExit("Usage: python -m app.ingest.owid_metric <metric>|--all [local.csv]")
    if sys.argv[1] == "--all":
        for m in METRICS:
            load(m)
    else:
        load(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)


if __name__ == "__main__":
    main()