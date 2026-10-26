import csv
from pathlib import Path

from sqlalchemy.dialects.postgresql import insert

from .db import SessionLocal
from .models import Product


def main():
    path = Path(__file__).resolve().parents[3] / "data" / "seed" / "products.csv"
    print(f"Reading {path}")
    count = 0
    with open(path, newline="", encoding="utf-8") as f, SessionLocal() as db:
        for r in csv.DictReader(f):
            vals = dict(
                slug=r["slug"],
                name=r["name"],
                category=r["category"],
                product_type=r["product_type"],
                hs_code=r["hs_code"] or None,
                price_unit=r["price_unit"] or None,
                has_price_series=False,
            )
            stmt = insert(Product).values(**vals).on_conflict_do_update(
                index_elements=["slug"],
                set_={k: v for k, v in vals.items() if k not in ("slug", "has_price_series")},
            )
            db.execute(stmt)
            count += 1
        db.commit()
    print(f"Seed complete: {count} products")


if __name__ == "__main__":
    main()