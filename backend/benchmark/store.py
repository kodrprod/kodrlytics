"""Local benchmark store. Reads JSON files from data/benchmarks/."""
from __future__ import annotations
import json
from pathlib import Path
from dataclasses import dataclass
from typing import Optional


@dataclass
class BenchmarkMetric:
    metric: str
    median: float
    p25: float
    p75: float
    source: str
    year: int
    unit: str


class BenchmarkStore:
    def __init__(self, data_dir: Optional[Path] = None):
        if data_dir is None:
            data_dir = Path(__file__).parent.parent.parent / "data" / "benchmarks"
        self._data: dict[str, dict[str, BenchmarkMetric]] = {}
        self._load(data_dir)

    def _load(self, data_dir: Path) -> None:
        for f in data_dir.glob("*.json"):
            raw = json.loads(f.read_text())
            nace_prefix = raw.get("nace_prefix", f.stem.split("_")[0])
            metrics: dict[str, BenchmarkMetric] = {}
            for k, v in raw.get("metrics", {}).items():
                metrics[k] = BenchmarkMetric(
                    metric=k,
                    median=v["median"], p25=v["p25"], p75=v["p75"],
                    source=v.get("source", ""), year=v.get("year", 0),
                    unit=v.get("unit", "")
                )
            self._data[nace_prefix] = metrics

    def get(self, nace_code: str, metric: str) -> Optional[BenchmarkMetric]:
        """Look up by full NACE code or prefix (e.g. 'C25' → try 'C25', then 'C')."""
        for key in [nace_code, nace_code[:2], nace_code[:1]]:
            if key in self._data and metric in self._data[key]:
                return self._data[key][metric]
        return None

    def available_nace_codes(self) -> list[str]:
        return list(self._data.keys())
