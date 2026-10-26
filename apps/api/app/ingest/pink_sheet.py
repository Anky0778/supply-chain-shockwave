"""Load World Bank Pink Sheet monthly prices into price_observation.

Usage (from apps/api, venv active):
    python -m app.ingest.pink_sheet --file ..\\..\\data\\raw\\pink_sheet_monthly.xlsx --list
    python -m app.ingest.pink_sheet --file ..\\..\\data\\raw\\pink_sheet_monthly.xlsx
"""
import argparse
import re
from datetime import date, datetime, timezone

import pandas as pd
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from ..db import SessionLocal
from ..models import DataSource, IngestionRun, PriceObservation, Product

SOURCE_CODE = "worldbank_pink_sheet"
DATE_RE = re.compile(r"^(\d{4})M(\d{2})$")

# product slug -> acceptable Pink Sheet column names (normalised). First match wins.
# Names change between releases, so unmatched products are reported, never guessed.
COLUMN_MAP = {
    "copper": ["copper"],
    "aluminium": ["aluminum", "aluminium"],
    "nickel": ["nickel"],
    "zinc": ["zinc"],
    "tin": ["tin"],
    "lead": ["lead"],
    "iron-ore": ["iron ore, cfr spot", "iron ore"],
    "gold": ["gold"],
    "silver": ["silver"],
    "platinum": ["platinum"],
    "crude-oil": ["crude oil, average"],
    "natural-gas": ["natural gas, us", "natural gas, u.s."],
    "coal": ["coal, australian", "coal, australia"],
    "wheat": ["wheat, us hrw", "wheat, us srw"],
    "maize": ["maize"],
    "rice": ["rice, thai 5%"],
    "soybeans": ["soybeans"],
    "palm-oil": ["palm oil"],
    "sugar": ["sugar, world"],
    "coffee": ["coffee, arabica"],
    "cocoa": ["cocoa"],
    "cotton": ["cotton, a index"],
    "rubber": ["rubber, rss3", "rubber, tsr20"],
    "urea": ["urea"],
}


def norm(text) -> str:
    s = str(text).lower().replace("*", "")
    s = re.sub(r"\b[a-z]/", "", s)  # footnote markers like "a/"
    return re.sub(r"\s+", " ", s).strip()


def clean_unit(text) -> str | None:
    if pd.isna(text):
        return None
    return str(text).strip().strip("()").replace("$", "USD").replace(" ", "")


def read_pink_sheet(path):
    xl = pd.ExcelFile(path)
    sheet = next((s for s in xl.sheet_names if "monthly prices" in s.lower()), None)
    if sheet is None:
        raise SystemExit(f"No 'Monthly Prices' sheet found. Sheets: {xl.sheet_names}")
    raw = xl.parse(sheet, header=None)

    first = next(
        (i for i, v in raw.iloc[:, 0].items()
         if isinstance(v, str) and DATE_RE.match(v.strip())),
        None,
    )
    if first is None:
        raise SystemExit("Could not find data rows (expected dates like 1960M01).")

    # Walk upward: first dense row is the units row, the next is the names row.
    header_rows, i = [], first - 1
    while i >= 0 and len(header_rows) < 2:
        if raw.iloc[i].notna().sum() >= 3:
            header_rows.append(i)
        i -= 1
    if len(header_rows) < 2:
        raise SystemExit("Could not locate the names/units header rows.")
    units_row, names_row = header_rows

    columns = {}
    for j in range(1, raw.shape[1]):
        name = raw.iat[names_row, j]
        if pd.notna(name):
            columns[j] = {"name": norm(name), "label": " ".join(str(name).split()),
                          "unit": clean_unit(raw.iat[units_row, j])}

    data = raw.iloc[first:].copy()
    data = data[data.iloc[:, 0].astype(str).str.strip().str.match(DATE_RE)]
    return columns, data


def to_date(label: str) -> date:
    m = DATE_RE.match(label.strip())
    return date(int(m.group(1)), int(m.group(2)), 1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", required=True)
    ap.add_argument("--list", action="store_true", help="show detected columns and exit")
    args = ap.parse_args()

    columns, data = read_pink_sheet(args.file)
    print(f"Detected {len(columns)} series, {len(data)} monthly rows "
          f"({data.iat[0, 0]} to {data.iat[-1, 0]})")

    if args.list:
        for j, c in columns.items():
            print(f"  col {j:>3}: {c['label']}  [{c['unit']}]")
        return

    by_name = {c["name"]: (j, c) for j, c in columns.items()}

    with SessionLocal() as db:
        src = db.scalar(select(DataSource).where(DataSource.code == SOURCE_CODE))
        if src is None:
            src = DataSource(
                code=SOURCE_CODE,
                name="World Bank Commodity Price Data (The Pink Sheet)",
                url="https://www.worldbank.org/en/research/commodity-markets",
                licence_note="Attribute: World Bank Commodity Price Data (The Pink Sheet). "
                             "Confirm licence terms on the World Bank site before publishing.",
                update_frequency="monthly",
            )
            db.add(src)
            db.flush()

        run = IngestionRun(source_id=src.id, status="running")
        db.add(run)
        db.flush()

        try:
            products = {p.slug: p for p in db.scalars(select(Product))}
            rows, matched, unmatched, rows_read = [], [], [], 0

            for slug, candidates in COLUMN_MAP.items():
                if slug not in products:
                    continue
                hit = next((by_name[c] for c in candidates if c in by_name), None)
                if hit is None:
                    unmatched.append(slug)
                    continue
                j, col = hit
                unit = col["unit"] or products[slug].price_unit
                series = pd.to_numeric(data.iloc[:, j], errors="coerce")  # ".." -> NaN
                n = 0
                for label, val in zip(data.iloc[:, 0], series):
                    if pd.isna(val):
                        continue
                    rows.append(dict(product_id=products[slug].id,
                                     observed_on=to_date(label),
                                     value=round(float(val), 4), unit=unit,
                                     currency="USD", source_id=src.id, run_id=run.id))
                    n += 1
                rows_read += n
                products[slug].has_price_series = n > 0
                products[slug].price_unit = unit
                matched.append((slug, col["label"], unit, n))

            for k in range(0, len(rows), 2000):
                stmt = insert(PriceObservation).values(rows[k:k + 2000])
                stmt = stmt.on_conflict_do_update(
                    constraint="uq_price_obs",
                    set_={"value": stmt.excluded.value, "unit": stmt.excluded.unit,
                          "run_id": stmt.excluded.run_id},
                )
                db.execute(stmt)

            run.status = "success"
            run.rows_read = rows_read
            run.rows_written = len(rows)
            run.finished_at = datetime.now(timezone.utc)
            db.commit()
        except Exception:
            db.rollback()
            raise

    print("\nMatched:")
    for slug, label, unit, n in matched:
        print(f"  {slug:<12} <- {label:<28} {unit:<14} {n} observations")
    if unmatched:
        print("\nNOT matched (no column found; they stay without a price series):")
        for s in unmatched:
            print(f"  {s}")
    print(f"\nDone. {len(rows)} price rows upserted.")


if __name__ == "__main__":
    main()