from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class Check:
    name: str
    passed: bool
    detail: str = ""


@dataclass
class Report:
    id: str
    layer: str
    status: str
    tier: str
    checks: list[Check]

    @property
    def passed(self) -> bool:
        return all(check.passed for check in self.checks)


def write_report(report: Report, directory: Path) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / f"{report.id}.json"
    data = asdict(report)
    data["passed"] = report.passed
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    return path
