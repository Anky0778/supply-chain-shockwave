"""Generate plain-language 'everyday impact' background (AI-written, unverified, no numbers).

Usage (from apps/api):
    python -m app.generate_drafts maize
    python -m app.generate_drafts --all
"""
import json
import sys
import time

from sqlalchemy import delete, select

from .config import settings
from .db import SessionLocal
from .llm import chat
from .models import MaterialCandidate, Product

PROMPT = """You are writing plain-language background for ordinary households. For the commodity \
"{material}", list 8 everyday goods or services a typical household buys whose prices can be \
affected by changes in the price of {material}. Order them by how directly and strongly the link works.
Respond ONLY with a JSON array of 8 objects with these keys:
"product": a short everyday name (for example "Chicken and eggs"),
"link_type": exactly one of "direct", "indirect", "minor",
"mechanism": 3 to 4 lines explaining how a change in the price of {material} reaches \
this product's price,
"delay": exactly one of "weeks", "months", "a year or more".
Rules: you can include numbers, percentages but make sure they are easy to understand also, Only include real links. No markdown, no commentary."""

LINKS = {"direct", "indirect", "minor"}
DELAYS = {"weeks", "months", "a year or more"}


def generate(db, p: Product) -> int:
    text = chat(PROMPT.format(material=p.name))
    s, e = text.find("["), text.rfind("]")
    if s == -1 or e == -1:
        raise ValueError(f"No JSON array in model output: {text[:200]}")
    items = json.loads(text[s:e + 1])

    clean, seen = [], set()
    for it in items:
        name = str(it.get("product", "")).strip()[:200]
        if not name or name.lower() in seen:
            continue
        seen.add(name.lower())
        link = str(it.get("link_type", "")).strip().lower()
        delay = str(it.get("delay", "")).strip().lower()
        clean.append(dict(
            product=name,
            link=link if link in LINKS else "indirect",
            why=str(it.get("mechanism", "")).strip()[:600],
            delay=delay if delay in DELAYS else None,
        ))
    if not clean:
        raise ValueError("Model returned no usable items")

    db.execute(delete(MaterialCandidate).where(MaterialCandidate.material_id == p.id))
    for rank, c in enumerate(clean, 1):
        db.add(MaterialCandidate(
            material_id=p.id, ai_rank=rank, downstream_product=c["product"], why=c["why"],
            link_type=c["link"], delay=c["delay"], model=settings.groq_model,
        ))
    db.commit()
    return len(clean)


def main():
    if len(sys.argv) < 2:
        raise SystemExit("Usage: python -m app.generate_drafts <product-slug> | --all")
    with SessionLocal() as db:
        if sys.argv[1] == "--all":
            targets = db.scalars(select(Product).order_by(Product.name)).all()
        else:
            p = db.scalar(select(Product).where(Product.slug == sys.argv[1]))
            if not p:
                raise SystemExit(f"Unknown product slug: {sys.argv[1]}")
            targets = [p]
        for p in targets:
            try:
                print(f"{p.slug}: stored {generate(db, p)} everyday-impact items")
            except Exception as exc:  # keep going on rate limits or bad output
                db.rollback()
                print(f"{p.slug}: FAILED ({exc})")
            if len(targets) > 1:
                time.sleep(4)


if __name__ == "__main__":
    main()