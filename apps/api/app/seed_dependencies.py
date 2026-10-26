import csv
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from .db import SessionLocal
from .models import Product, ProductDependency

KEY = ("product_id", "downstream_name", "geography", "reference_label")


def main():
    path = Path(__file__).resolve().parents[3] / "data" / "seed" / "dependencies.csv"
    n, skipped = 0, []
    with open(path, newline="", encoding="utf-8") as f, SessionLocal() as db:
        ids = {p.slug: p.id for p in db.scalars(select(Product))}
        for r in csv.DictReader(f):
            pid = ids.get(r["material_slug"])
            if pid is None:
                skipped.append(r["material_slug"])
                continue
            vals = dict(
                product_id=pid,
                downstream_name=r["downstream_name"],
                kind=r["kind"],
                share_pct=float(r["share_pct"]) if r["share_pct"] else None,
                geography=r["geography"],
                reference_label=r["reference_label"],
                source_name=r["source_name"],
                source_url=r["source_url"],
                confidence=r["confidence"],
                note=r["note"] or None,
            )
            stmt = insert(ProductDependency).values(**vals).on_conflict_do_update(
                constraint="uq_dependency",
                set_={k: v for k, v in vals.items() if k not in KEY},
            )
            db.execute(stmt)
            n += 1
        db.commit()
    print(f"Dependencies loaded: {n}" + (f" | skipped unknown products: {skipped}" if skipped else ""))


if __name__ == "__main__":
    main()