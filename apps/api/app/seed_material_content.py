import csv
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from .db import SessionLocal
from .models import Product, ProductMaterialContent

KEY = ("material_id", "downstream_product", "unit_basis", "source_url")


def main():
    path = Path(__file__).resolve().parents[3] / "data" / "seed" / "material_content.csv"
    loaded, skipped = 0, 0
    with open(path, newline="", encoding="utf-8") as f, SessionLocal() as db:
        ids = {p.slug: p.id for p in db.scalars(select(Product))}
        for r in csv.DictReader(f):
            if not (r["kg_per_unit"].strip() and r["source_url"].strip()) or r["material_slug"] not in ids:
                skipped += 1  # unsourced rows are never loaded
                continue
            vals = dict(
                material_id=ids[r["material_slug"]],
                downstream_product=r["downstream_product"],
                unit_basis=r["unit_basis"],
                kg_per_unit=float(r["kg_per_unit"]),
                reference_year=int(r["reference_year"]) if r["reference_year"].strip() else None,
                source_name=r["source_name"],
                source_url=r["source_url"],
                note=r["note"] or None,
            )
            stmt = insert(ProductMaterialContent).values(**vals).on_conflict_do_update(
                constraint="uq_material_content",
                set_={k: v for k, v in vals.items() if k not in KEY},
            )
            db.execute(stmt)
            loaded += 1
        db.commit()
    print(f"Loaded {loaded} verified rows, skipped {skipped} unsourced or unknown rows")


if __name__ == "__main__":
    main()