"""Ask the LLM which priced commodities plausibly link to a target. Stored as hypotheses.

Usage (from apps/api):
    python -m app.driver_ai coal
    python -m app.driver_ai --all
"""
import json
import sys
import time

from sqlalchemy import delete, select

from .config import settings
from .llm import chat
from .models import DriverLink, Product

RELATIONS = {"input_cost", "substitute", "complement", "energy", "demand_proxy", "co_produced", "other"}

PROMPT = """You are an economist. Target commodity: "{target}".
Below is every other commodity price series available. Choose up to 8 whose prices plausibly \
influence, or are influenced by, the price of {target}. Use ONLY slugs from this list, exactly as written.

Available:
{catalogue}

Respond ONLY with a JSON array of objects with keys:
"slug": a slug from the list,
"relation": one of "input_cost", "substitute", "complement", "energy", "demand_proxy", "co_produced", "other",
"mechanism": one plain sentence naming the economic channel (no numbers).
Order by plausibility. Only include links with a real economic channel. If none are plausible, return [].
No markdown, no commentary."""


def generate_links(db, target: Product) -> int:
    cands = db.scalars(
        select(Product)
        .where(Product.has_price_series.is_(True), Product.id != target.id)
        .order_by(Product.name)
    ).all()
    catalogue = "\n".join(f"- {c.slug}: {c.name} ({c.category})" for c in cands)
    text = chat(PROMPT.format(target=target.name, catalogue=catalogue))
    s, e = text.find("["), text.rfind("]")
    if s == -1 or e == -1:
        raise ValueError(f"No JSON array in model output: {text[:200]}")
    items = json.loads(text[s:e + 1])

    valid = {c.slug: c for c in cands}
    clean, seen = [], set()
    for it in items:
        slug = str(it.get("slug", "")).strip()
        if slug not in valid or slug in seen:   # ignore invented or repeated slugs
            continue
        seen.add(slug)
        rel = str(it.get("relation", "other")).strip().lower()
        clean.append((valid[slug], rel if rel in RELATIONS else "other",
                      str(it.get("mechanism", "")).strip()[:400]))

    db.execute(delete(DriverLink).where(DriverLink.target_id == target.id))
    for prod, rel, mech in clean[:8]:
        db.add(DriverLink(target_id=target.id, driver_id=prod.id, mechanism=mech,
                          relation=rel, model=settings.groq_model))
    db.commit()
    return len(clean[:8])


def main():
    from .db import SessionLocal
    if len(sys.argv) < 2:
        raise SystemExit("Usage: python -m app.driver_ai <slug> | --all")
    with SessionLocal() as db:
        if sys.argv[1] == "--all":
            targets = db.scalars(select(Product).where(Product.has_price_series.is_(True))
                                 .order_by(Product.name)).all()
        else:
            t = db.scalar(select(Product).where(Product.slug == sys.argv[1]))
            if not t:
                raise SystemExit(f"Unknown slug: {sys.argv[1]}")
            targets = [t]
        for t in targets:
            try:
                print(f"{t.slug}: stored {generate_links(db, t)} AI-proposed links")
            except Exception as exc:
                db.rollback()
                print(f"{t.slug}: FAILED ({exc})")
            if len(targets) > 1:
                time.sleep(4)


if __name__ == "__main__":
    main()