from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (Boolean, Date, DateTime, ForeignKey, Index, Integer,
                        Numeric, String, Text, UniqueConstraint, func)
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


class DataSource(Base):
    __tablename__ = "data_source"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(40), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    url: Mapped[str | None] = mapped_column(String(500))
    licence_note: Mapped[str | None] = mapped_column(Text)
    update_frequency: Mapped[str | None] = mapped_column(String(40))


class Product(Base):
    __tablename__ = "product"
    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(80), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    category: Mapped[str] = mapped_column(String(60), index=True)
    product_type: Mapped[str] = mapped_column(String(30))
    hs_code: Mapped[str | None] = mapped_column(String(10), index=True)
    price_unit: Mapped[str | None] = mapped_column(String(40))
    has_price_series: Mapped[bool] = mapped_column(Boolean, default=False)
    description: Mapped[str | None] = mapped_column(Text)


class Country(Base):
    __tablename__ = "country"
    iso3: Mapped[str] = mapped_column(String(3), primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    region: Mapped[str | None] = mapped_column(String(60))


class IngestionRun(Base):
    __tablename__ = "ingestion_run"
    id: Mapped[int] = mapped_column(primary_key=True)
    source_id: Mapped[int] = mapped_column(ForeignKey("data_source.id"))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(20), default="running")
    rows_read: Mapped[int] = mapped_column(Integer, default=0)
    rows_written: Mapped[int] = mapped_column(Integer, default=0)


class PriceObservation(Base):
    __tablename__ = "price_observation"
    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("product.id"))
    observed_on: Mapped[date] = mapped_column(Date)
    value: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    unit: Mapped[str] = mapped_column(String(40))
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    source_id: Mapped[int] = mapped_column(ForeignKey("data_source.id"))
    run_id: Mapped[int | None] = mapped_column(ForeignKey("ingestion_run.id"))
    __table_args__ = (
        UniqueConstraint("product_id", "observed_on", "source_id", name="uq_price_obs"),
        Index("ix_price_product_date", "product_id", "observed_on"),
    )


class TradeObservation(Base):
    __tablename__ = "trade_observation"
    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("product.id"))
    reporter_iso3: Mapped[str] = mapped_column(ForeignKey("country.iso3"))
    partner_iso3: Mapped[str] = mapped_column(ForeignKey("country.iso3"))
    flow: Mapped[str] = mapped_column(String(10))
    year: Mapped[int] = mapped_column(Integer)
    value_usd: Mapped[Decimal | None] = mapped_column(Numeric(20, 2))
    net_weight_kg: Mapped[Decimal | None] = mapped_column(Numeric(20, 2))
    source_id: Mapped[int] = mapped_column(ForeignKey("data_source.id"))
    __table_args__ = (
        UniqueConstraint("product_id", "reporter_iso3", "partner_iso3", "flow",
                         "year", "source_id", name="uq_trade_obs"),
    )
class ProductDependency(Base):
    """Documented link from a material to a downstream sector or product."""
    __tablename__ = "product_dependency"
    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("product.id"), index=True)
    downstream_name: Mapped[str] = mapped_column(String(200))
    kind: Mapped[str] = mapped_column(String(30))  # end_use_sector | product
    share_pct: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    geography: Mapped[str] = mapped_column(String(60))
    reference_label: Mapped[str] = mapped_column(String(80))
    source_name: Mapped[str] = mapped_column(String(300))
    source_url: Mapped[str] = mapped_column(String(500))
    confidence: Mapped[str] = mapped_column(String(10))
    note: Mapped[str | None] = mapped_column(Text)
    __table_args__ = (
        UniqueConstraint("product_id", "downstream_name", "geography",
                         "reference_label", name="uq_dependency"),
    )
    
class ProductMaterialContent(Base):
    """Verified, sourced material content of a downstream product (kg per unit)."""
    __tablename__ = "product_material_content"
    id: Mapped[int] = mapped_column(primary_key=True)
    material_id: Mapped[int] = mapped_column(ForeignKey("product.id"), index=True)
    downstream_product: Mapped[str] = mapped_column(String(200))
    unit_basis: Mapped[str] = mapped_column(String(60))
    kg_per_unit: Mapped[Decimal] = mapped_column(Numeric(12, 4))
    reference_year: Mapped[int | None] = mapped_column(Integer)
    source_name: Mapped[str] = mapped_column(String(300))
    source_url: Mapped[str] = mapped_column(String(500))
    note: Mapped[str | None] = mapped_column(Text)
    __table_args__ = (
        UniqueConstraint("material_id", "downstream_product", "unit_basis",
                         "source_url", name="uq_material_content"),
    )
    
class MaterialCandidate(Base):
    """AI-suggested downstream products. Unverified; never used in calculations."""
    __tablename__ = "material_candidate"
    id: Mapped[int] = mapped_column(primary_key=True)
    material_id: Mapped[int] = mapped_column(ForeignKey("product.id"), index=True)
    ai_rank: Mapped[int] = mapped_column(Integer)
    downstream_product: Mapped[str] = mapped_column(String(200))
    why: Mapped[str | None] = mapped_column(Text)
    unit_basis: Mapped[str | None] = mapped_column(String(60))
    ai_estimate: Mapped[str | None] = mapped_column(String(200))
    link_type: Mapped[str | None] = mapped_column(String(20))
    delay: Mapped[str | None] = mapped_column(String(30))
    model: Mapped[str | None] = mapped_column(String(80))
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (
        UniqueConstraint("material_id", "downstream_product", name="uq_material_candidate"),
    )
    
class CountryMetric(Base):
    """Country-level indicator from a published dataset (for example share of electricity from coal)."""
    __tablename__ = "country_metric"
    id: Mapped[int] = mapped_column(primary_key=True)
    metric: Mapped[str] = mapped_column(String(60), index=True)
    iso3: Mapped[str] = mapped_column(String(3))
    country_name: Mapped[str] = mapped_column(String(120))
    year: Mapped[int] = mapped_column(Integer)
    value: Mapped[Decimal] = mapped_column(Numeric(16, 4))
    unit: Mapped[str] = mapped_column(String(40))
    source_name: Mapped[str] = mapped_column(String(300))
    source_url: Mapped[str] = mapped_column(String(500))
    __table_args__ = (UniqueConstraint("metric", "iso3", "year", name="uq_country_metric"),)
    
class DriverLink(Base):
    """AI-proposed link between two priced commodities. A hypothesis, tested separately on the data."""
    __tablename__ = "driver_link"
    id: Mapped[int] = mapped_column(primary_key=True)
    target_id: Mapped[int] = mapped_column(ForeignKey("product.id"), index=True)
    driver_id: Mapped[int] = mapped_column(ForeignKey("product.id"))
    mechanism: Mapped[str | None] = mapped_column(Text)
    relation: Mapped[str | None] = mapped_column(String(30))
    model: Mapped[str | None] = mapped_column(String(80))
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (UniqueConstraint("target_id", "driver_id", name="uq_driver_link"),)