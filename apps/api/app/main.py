from datetime import date

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from .analytics import compute_insights
from .config import settings
from .driver_ai import generate_links
from .drivers import compute_drivers
from .forecasting import run_forecasts
from .models import (CountryMetric, DriverLink, MaterialCandidate, PriceObservation, Product,
                     ProductDependency, ProductMaterialContent)
from .impact_ai import claim, generate_impact
from .db import SessionLocal, get_db
app = FastAPI(title="Supply Chain Shockwave API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_methods=["GET"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/products")
def list_products(
    q: str | None = None,
    category: str | None = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    db: Session = Depends(get_db),
):
    stmt = select(Product).order_by(Product.name).limit(limit).offset(offset)
    if q:
        stmt = stmt.where(Product.name.ilike(f"%{q}%"))
    if category:
        stmt = stmt.where(Product.category == category)
    rows = db.scalars(stmt).all()
    return [
        {
            "slug": p.slug,
            "name": p.name,
            "category": p.category,
            "product_type": p.product_type,
            "hs_code": p.hs_code,
            "has_price_series": p.has_price_series,
        }
        for p in rows
    ]


@app.get("/products/{slug}")
def get_product(slug: str, db: Session = Depends(get_db)):
    p = db.scalar(select(Product).where(Product.slug == slug))
    if not p:
        raise HTTPException(404, f"Product '{slug}' not found")
    return {
        "slug": p.slug,
        "name": p.name,
        "category": p.category,
        "hs_code": p.hs_code,
        "price_unit": p.price_unit,
        "has_price_series": p.has_price_series,
        "description": p.description,
    }


@app.get("/products/{slug}/prices")
def get_prices(
    slug: str,
    start: date | None = None,
    end: date | None = None,
    db: Session = Depends(get_db),
):
    p = db.scalar(select(Product).where(Product.slug == slug))
    if not p:
        raise HTTPException(404, f"Product '{slug}' not found")
    if not p.has_price_series:
        raise HTTPException(404, f"No price series available for '{slug}'")
    stmt = (
        select(PriceObservation.observed_on, PriceObservation.value)
        .where(PriceObservation.product_id == p.id)
        .order_by(PriceObservation.observed_on)
    )
    if start:
        stmt = stmt.where(PriceObservation.observed_on >= start)
    if end:
        stmt = stmt.where(PriceObservation.observed_on <= end)
    rows = db.execute(stmt).all()
    return {
        "slug": p.slug,
        "unit": p.price_unit,
        "currency": "USD",
        "basis": "Nominal monthly average",
        "source": "World Bank Commodity Price Data (The Pink Sheet)",
        "points": [{"date": r.observed_on.isoformat(), "value": float(r.value)} for r in rows],
    }


@app.get("/products/{slug}/insights")
def get_insights(slug: str, db: Session = Depends(get_db)):
    p = db.scalar(select(Product).where(Product.slug == slug))
    if not p:
        raise HTTPException(404, f"Product '{slug}' not found")
    if not p.has_price_series:
        raise HTTPException(404, f"No price series available for '{slug}'")
    rows = db.execute(
        select(PriceObservation.observed_on, PriceObservation.value)
        .where(PriceObservation.product_id == p.id)
        .order_by(PriceObservation.observed_on)
    ).all()
    return compute_insights([(r.observed_on, float(r.value)) for r in rows], p.price_unit or "")


@app.get("/products/{slug}/dependencies")
def get_dependencies(slug: str, db: Session = Depends(get_db)):
    p = db.scalar(select(Product).where(Product.slug == slug))
    if not p:
        raise HTTPException(404, f"Product '{slug}' not found")
    rows = db.scalars(
        select(ProductDependency)
        .where(ProductDependency.product_id == p.id)
        .order_by(ProductDependency.share_pct.desc().nulls_last())
    ).all()
    return [
        {
            "downstream_name": d.downstream_name,
            "kind": d.kind,
            "share_pct": float(d.share_pct) if d.share_pct is not None else None,
            "geography": d.geography,
            "reference_label": d.reference_label,
            "source_name": d.source_name,
            "source_url": d.source_url,
            "confidence": d.confidence,
            "note": d.note,
        }
        for d in rows
    ]


UNIT_TO_USD_PER_KG = {"USD/mt": 0.001, "USD/kg": 1.0}


@app.get("/products/{slug}/exposure")
def get_exposure(
    slug: str,
    price_change_pct: float = Query(10, ge=-80, le=200),
    db: Session = Depends(get_db),
):
    p = db.scalar(select(Product).where(Product.slug == slug))
    if not p:
        raise HTTPException(404, f"Product '{slug}' not found")
    factor = UNIT_TO_USD_PER_KG.get(p.price_unit or "")
    if factor is None:
        raise HTTPException(422, f"Exposure calculation does not support unit '{p.price_unit}'")
    latest = db.execute(
        select(PriceObservation.observed_on, PriceObservation.value)
        .where(PriceObservation.product_id == p.id)
        .order_by(desc(PriceObservation.observed_on))
        .limit(1)
    ).first()
    if latest is None:
        raise HTTPException(404, f"No price series available for '{slug}'")

    price_per_kg = float(latest.value) * factor
    rows = db.scalars(
        select(ProductMaterialContent).where(ProductMaterialContent.material_id == p.id)
    ).all()
    items = []
    for r in rows:
        kg = float(r.kg_per_unit)
        base = kg * price_per_kg
        items.append({
            "downstream_product": r.downstream_product,
            "unit_basis": r.unit_basis,
            "kg_per_unit": kg,
            "material_cost_per_unit_usd": base,
            "change_per_unit_usd": base * price_change_pct / 100,
            "source_name": r.source_name,
            "source_url": r.source_url,
            "reference_year": r.reference_year,
        })
    items.sort(key=lambda i: i["change_per_unit_usd"], reverse=True)
    return {
        "scenario": "user-defined",
        "price_change_pct": price_change_pct,
        "reference_price": {"date": latest.observed_on.isoformat(), "usd_per_kg": price_per_kg},
        "formula": "change per unit = kg per unit × reference price (USD/kg) × price change %",
        "assumption": "Uses the benchmark monthly average price, not what any manufacturer actually pays. "
                      "Excludes hedging, contracts, processing costs and pass-through to consumers.",
        "items": items,
    }


@app.get("/products/{slug}/candidates")
def get_candidates(slug: str, db: Session = Depends(get_db)):
    p = db.scalar(select(Product).where(Product.slug == slug))
    if not p:
        raise HTTPException(404, f"Product '{slug}' not found")
    rows = db.scalars(
        select(MaterialCandidate)
        .where(MaterialCandidate.material_id == p.id)
        .order_by(MaterialCandidate.ai_rank)
    ).all()
    return {
        "model": rows[0].model if rows else None,
        "generated_at": rows[0].generated_at.isoformat() if rows else None,
        "items": [
            {"ai_rank": r.ai_rank, "downstream_product": r.downstream_product, "why": r.why,
             "link_type": r.link_type, "delay": r.delay}
            for r in rows
        ],
    }


_FORECAST_CACHE: dict = {}


@app.get("/products/{slug}/forecast")
def get_forecast(slug: str, db: Session = Depends(get_db)):
    p = db.scalar(select(Product).where(Product.slug == slug))
    if not p:
        raise HTTPException(404, f"Product '{slug}' not found")
    if not p.has_price_series:
        raise HTTPException(404, f"No price series available for '{slug}'")
    rows = db.execute(
        select(PriceObservation.observed_on, PriceObservation.value)
        .where(PriceObservation.product_id == p.id)
        .order_by(PriceObservation.observed_on)
    ).all()
    key = (slug, rows[-1].observed_on, len(rows))
    if key not in _FORECAST_CACHE:
        _FORECAST_CACHE[key] = run_forecasts(
            [(r.observed_on, float(r.value)) for r in rows], p.price_unit or ""
        )
    return _FORECAST_CACHE[key]


_OVERVIEW_CACHE: dict = {}


@app.get("/overview")
def get_overview(db: Session = Depends(get_db)):
    prods = db.scalars(
        select(Product).where(Product.has_price_series.is_(True)).order_by(Product.name)
    ).all()
    rows = db.execute(
        select(PriceObservation.product_id, PriceObservation.observed_on, PriceObservation.value)
        .where(PriceObservation.product_id.in_([p.id for p in prods]))
        .order_by(PriceObservation.product_id, PriceObservation.observed_on)
    ).all()
    key = (len(rows), max((r.observed_on for r in rows), default=None))
    if key in _OVERVIEW_CACHE:
        return _OVERVIEW_CACHE[key]

    by: dict = {}
    for r in rows:
        by.setdefault(r.product_id, []).append((r.observed_on, float(r.value)))

    items = []
    for p in prods:
        pts = by.get(p.id, [])
        ins = compute_insights(pts, p.price_unit or "")
        if not ins.get("sufficient_data"):
            continue
        items.append({
            "slug": p.slug,
            "name": p.name,
            "category": p.category,
            "unit": p.price_unit,
            "latest_date": ins["latest"]["date"],
            "latest_value": ins["latest"]["value"],
            "change_12m_pct": ins["changes"].get("12m", {}).get("pct"),
            "percentile_10y": ins["percentile_10y"]["pct"],
            "volatility_pct": ins.get("volatility_3y", {}).get("annualised_pct"),
            "sparkline": [v for _, v in pts[-60:]],
        })
    total = db.scalar(select(func.count()).select_from(Product))
    result = {
        "count": len(items),
        "total_products": total,
        "latest_date": max((i["latest_date"] for i in items), default=None),
        "items": items,
    }
    _OVERVIEW_CACHE[key] = result
    return result


_DRIVER_ATTEMPTED: set = set()


def _generate_links_bg(slug: str) -> None:
    with SessionLocal() as s:
        try:
            p = s.scalar(select(Product).where(Product.slug == slug))
            if p is not None:
                generate_links(s, p)
        except Exception:
            s.rollback()
            _DRIVER_ATTEMPTED.discard(slug)  # allow another try on a later visit


@app.get("/products/{slug}/drivers")
def get_drivers(slug: str, background: BackgroundTasks, db: Session = Depends(get_db)):
    p = db.scalar(select(Product).where(Product.slug == slug))
    if not p:
        raise HTTPException(404, f"Product '{slug}' not found")
    if not p.has_price_series:
        return {"configured": False, "items": []}

    count = db.scalar(select(func.count()).select_from(DriverLink).where(DriverLink.target_id == p.id))
    ai_pending = False
    if not count:
        ai_pending = True
        if slug not in _DRIVER_ATTEMPTED:
            _DRIVER_ATTEMPTED.add(slug)
            background.add_task(_generate_links_bg, slug)

    links = db.execute(
        select(DriverLink, Product)
        .join(Product, Product.id == DriverLink.driver_id)
        .where(DriverLink.target_id == p.id)
    ).all()

    priced = db.scalars(select(Product).where(Product.has_price_series.is_(True))).all()
    by_id = {x.id: x for x in priced}
    rows = db.execute(
        select(PriceObservation.product_id, PriceObservation.observed_on, PriceObservation.value)
        .order_by(PriceObservation.product_id, PriceObservation.observed_on)
    ).all()
    series: dict = {}
    for r in rows:
        if r.product_id in by_id:
            series.setdefault(by_id[r.product_id].slug, []).append((r.observed_on, float(r.value)))

    cfg = [(prod.slug, link.mechanism, link.relation, "ai") for link, prod in links]
    out = compute_drivers(slug, cfg, series, {x.slug: x.name for x in priced})
    if ai_pending:
        out["ai_pending"] = True
    return out


EXPOSURE_METRICS = {
    "coal": {
        "share": "electricity_share_coal",
        "generation": "electricity_generation",
        "title": "Where coal matters most for electricity",
    },
}


def _latest_by_country(db: Session, metric: str, window: int = 2):
    maxy = db.scalar(select(func.max(CountryMetric.year)).where(CountryMetric.metric == metric))
    if maxy is None:
        return {}, None
    rows = db.scalars(
        select(CountryMetric).where(CountryMetric.metric == metric, CountryMetric.year >= maxy - window)
    ).all()
    best: dict = {}
    for r in rows:
        if r.iso3 not in best or r.year > best[r.iso3].year:
            best[r.iso3] = r
    return best, maxy


@app.get("/products/{slug}/country-exposure")
def get_country_exposure(slug: str, db: Session = Depends(get_db)):
    cfg = EXPOSURE_METRICS.get(slug)
    if not cfg:
        return {"configured": False}
    share, year = _latest_by_country(db, cfg["share"])
    gen, _ = _latest_by_country(db, cfg["generation"])
    items = []
    for iso, s in share.items():
        g = gen.get(iso)
        if not g:
            continue
        sv, gv = float(s.value), float(g.value)
        items.append({"iso3": iso, "name": s.country_name, "share_pct": sv,
                      "generation_twh": gv, "coal_twh": sv / 100 * gv, "year": s.year})
    if not items:
        return {"configured": True, "items_found": 0}
    src = next(iter(share.values()))
    return {
        "configured": True,
        "title": cfg["title"],
        "year": year,
        "min_generation_twh_for_dependence_list": 20,
        "largest": sorted(items, key=lambda i: i["coal_twh"], reverse=True)[:12],
        "dependent": sorted([i for i in items if i["generation_twh"] >= 20],
                            key=lambda i: i["share_pct"], reverse=True)[:12],
        "source_name": src.source_name,
        "source_url": src.source_url,
    }

@app.get("/products/{slug}/impact")
def get_impact(slug: str, background: BackgroundTasks, db: Session = Depends(get_db)):
    p = db.scalar(select(Product).where(Product.slug == slug))
    if not p:
        raise HTTPException(404, f"Product '{slug}' not found")
    rows = db.scalars(
        select(MaterialCandidate)
        .where(MaterialCandidate.material_id == p.id)
        .order_by(MaterialCandidate.ai_rank)
    ).all()
    if rows:
        return {
            "status": "ready",
            "model": rows[0].model,
            "generated_at": rows[0].generated_at.isoformat(),
            "items": [
                {"ai_rank": r.ai_rank, "downstream_product": r.downstream_product, "why": r.why,
                 "link_type": r.link_type, "delay": r.delay}
                for r in rows
            ],
        }
    action = claim(slug)
    if action == "start":
        background.add_task(generate_impact, slug)
        return {"status": "generating", "items": []}
    return {"status": action, "items": []}