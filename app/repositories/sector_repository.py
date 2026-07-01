"""
Sector repository: loads the static symbol -> sector / sub-index mapping.

Source is a hand-maintained reference file (data/reference/symbol_sectors.csv),
not scraped data — sector classification changes rarely, so a static lookup is
sufficient rather than a live pipeline step.
"""

import csv
from pathlib import Path
from typing import Dict, NamedTuple, Optional

from app.logging_config import get_logger

logger = get_logger(__name__)


class SectorInfo(NamedTuple):
    sector: str
    sub_index: str


class SectorRepository:
    """Loads and serves the symbol -> sector/sub-index mapping."""

    def __init__(self, reference_data_dir: Path):
        self.path = reference_data_dir / "symbol_sectors.csv"
        self._by_symbol: Dict[str, SectorInfo] = {}

    def load(self) -> None:
        try:
            with open(self.path, encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    symbol = (row.get("symbol") or "").strip().upper()
                    if not symbol:
                        continue
                    self._by_symbol[symbol] = SectorInfo(
                        sector=(row.get("sector") or "").strip(),
                        sub_index=(row.get("sub_index") or "").strip(),
                    )
            logger.info("Loaded sector mapping for %d symbols from %s", len(self._by_symbol), self.path)
        except FileNotFoundError:
            logger.warning("Sector mapping file not found: %s (sector fields will be empty)", self.path)
            self._by_symbol = {}
        except Exception as e:
            logger.error("Failed to load sector mapping: %s", e)
            self._by_symbol = {}

    def get(self, symbol: str) -> Optional[SectorInfo]:
        return self._by_symbol.get(symbol.upper())

    def is_ready(self) -> bool:
        return len(self._by_symbol) > 0
