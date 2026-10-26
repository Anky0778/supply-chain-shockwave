"""On-demand AI analysis: how a commodity's price reaches everyday products."""
import json
import re
import threading
import time

from sqlalchemy import delete, select

from .analytics import compute_insights
from .config import settings
from .db import SessionLocal
from .llm import chat
from .models import MaterialCandidate, PriceObservation, Product

LINKS = {"direct", "indirect", "minor"}
DELAYS = {"weeks", "months", "a year or more"}
RETRY_AFTER = 120    # seconds before a failed generation may be retried
STALE_AFTER = 180    # seconds before a stuck "generating" state is abandoned
MAX_PER_HOUR = 40    # global cap, protects the free LLM quota

_STATE: dict[str, dict] = {}
_STARTS: list[float] = []
_LOCK = threading.Lock()

PROMPT = """You are an economist explaining commodity prices to ordinary households.
Commodity: "{material}".
Measured price context (from official data; refer to it only in words, never quote numbers):
{context}

List the 5 everyday goods or services whose prices are most affected by changes in the price of {material}, \
strongest link first. Respond ONLY with a JSON array of 5 objects with keys:
"product": short everyday name (for example "Chicken and eggs"),
"link_type": exactly one of "direct", "indirect", "minor",
"mechanism": exactly two plain sentences. First: the channel by which a change in the price of {material} \
reaches this product's price. Second: given the measured price context above (for example whether the price \
is currently high or low, rising or falling), what a household might notice,
"delay": exactly one of "weeks", "months", "a year or more".
Rules: no numbers, percentages or quantities anywhere. Only real, well-established links. \
No markdown, no commentary."""


def claim(slug: str) -> str:
    """Return 'start' if the caller should launch generation, else the current status."""
    now = time.time()
    with _LOCK:
        st = _STATE.get(slug)
        if st:
            age = now - st["since"]
            if st["status"] == "generating" and age < STALE_AFTER:
                return "generating"
            if st["status"] == "failed" and age < RETRY_AFTER:
                return "failed"
        _STARTS[:] = [t for t in _STARTS if now - t < 3600]
        if len(_STARTS) >= MAX_PER_HOUR:
            return "busy"
        _STARTS.append(now)
        _STATE[slug] = {"status": "generating", "since": now}
        return "start"


def generate_impact(slug: str) -> None:
    try:
        with SessionLocal() as db:
            p = db.scalar(select(Product).where(Product.slug == slug))
            if p is None:
                raise ValueError("unknown product")

            context = "No price history is available for this product."
            if p.has_price_series:
                rows = db.execute(
                    select(PriceObservation.observed_on, PriceObservation.value)
                    .where(PriceObservation.product_id == p.id)
                    .order_by(PriceObservation.observed_on)
                ).all()
                ins = compute_insights([(r.observed_on, float(r.value)) for r in rows], p.price_unit or "")
                if ins.get("sufficient_data"):
                    context = "\n".join(f"- {n}" for n in ins["notes"])

            text = chat(PROMPT.format(material=p.name, context=context))
            s, e = text.find("["), text.rfind("]")
            if s == -1 or e == -1:
                raise ValueError("model did not return a JSON array")
            items = json.loads(text[s:e + 1])

            clean, seen = [], set()
            for it in items:
                name = str(it.get("product", "")).strip()[:200]
                mech = str(it.get("mechanism", "")).strip()[:700]
                if not name or not mech or name.lower() in seen or re.search(r"\d", mech + name):
                    continue  # skip duplicates and anything that states figures
                seen.add(name.lower())
                link = str(it.get("link_type", "")).strip().lower()
                delay = str(it.get("delay", "")).strip().lower()
                clean.append((name, link if link in LINKS else "indirect", mech,
                              delay if delay in DELAYS else None))
            if len(clean) < 3:
                raise ValueError("too few usable items in the model output")

            db.execute(delete(MaterialCandidate).where(MaterialCandidate.material_id == p.id))
            for rank, (name, link, mech, delay) in enumerate(clean[:5], 1):
                db.add(MaterialCandidate(
                    material_id=p.id, ai_rank=rank, downstream_product=name, why=mech,
                    link_type=link, delay=delay, model=settings.groq_model,
                ))
            db.commit()
        with _LOCK:
            _STATE.pop(slug, None)
    except Exception as exc:
        with _LOCK:
            _STATE[slug] = {"status": "failed", "since": time.time(), "error": str(exc)[:200]}