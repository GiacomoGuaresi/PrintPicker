"""Print cost estimate from a tiered price list."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal


@dataclass(frozen=True)
class PriceTier:
    """From ``min_quantity`` photos up (until the next tier), each print costs ``unit_price``."""

    min_quantity: int
    unit_price: Decimal


@dataclass(frozen=True)
class FixedCost:
    """Added once per order (shipping, handling...)."""

    name: str
    amount: Decimal


@dataclass(frozen=True)
class Estimate:
    count: int
    unit_price: Decimal
    prints: Decimal
    fixed: Decimal

    @property
    def total(self) -> Decimal:
        return self.prints + self.fixed


@dataclass(frozen=True)
class PriceList:
    name: str
    tiers: tuple[PriceTier, ...]
    fixed_costs: tuple[FixedCost, ...] = field(default=())
    currency: str = "EUR"

    def __post_init__(self) -> None:
        tiers = tuple(sorted(self.tiers, key=lambda t: t.min_quantity))
        if not tiers or tiers[0].min_quantity > 1:
            raise ValueError("the first tier must start at 1 photo")
        if len({t.min_quantity for t in tiers}) != len(tiers):
            raise ValueError("two tiers start at the same quantity")
        if any(t.unit_price < 0 for t in tiers) or any(c.amount < 0 for c in self.fixed_costs):
            raise ValueError("prices cannot be negative")
        object.__setattr__(self, "tiers", tiers)

    def unit_price(self, count: int) -> Decimal:
        price = self.tiers[0].unit_price
        for tier in self.tiers:
            if count >= tier.min_quantity:
                price = tier.unit_price
        return price

    def estimate(self, count: int) -> Estimate:
        """The tier reached by ``count`` prices *all* the photos (quantity discount)."""
        if count <= 0:
            return Estimate(0, self.tiers[0].unit_price, Decimal(0), Decimal(0))
        unit = self.unit_price(count)
        fixed = sum((c.amount for c in self.fixed_costs), Decimal(0))
        return Estimate(count, unit, unit * count, fixed)

    def tier_ranges(self) -> list[tuple[int, int | None, Decimal]]:
        """``(from, to, price)`` rows for display; ``to`` is None for the last tier."""
        rows = []
        for i, tier in enumerate(self.tiers):
            upper = self.tiers[i + 1].min_quantity - 1 if i + 1 < len(self.tiers) else None
            rows.append((tier.min_quantity, upper, tier.unit_price))
        return rows

    # Serialization (settings) -------------------------------------------------------------

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "currency": self.currency,
            "tiers": [[t.min_quantity, str(t.unit_price)] for t in self.tiers],
            "fixed_costs": [[c.name, str(c.amount)] for c in self.fixed_costs],
        }

    @classmethod
    def from_dict(cls, data: dict) -> PriceList:
        return cls(
            name=str(data["name"]),
            currency=str(data.get("currency", "EUR")),
            tiers=tuple(PriceTier(int(q), Decimal(p)) for q, p in data["tiers"]),
            fixed_costs=tuple(
                FixedCost(str(n), Decimal(a)) for n, a in data.get("fixed_costs", [])
            ),
        )


# PhotoSì, 10×15 prints, prices checked on 2026-10-12.
DEFAULT_PRICE_LIST = PriceList(
    name="PhotoSì 10×15",
    tiers=(
        PriceTier(1, Decimal("0.35")),
        PriceTier(20, Decimal("0.30")),
        PriceTier(100, Decimal("0.25")),
        PriceTier(200, Decimal("0.19")),
        PriceTier(400, Decimal("0.16")),
    ),
)
