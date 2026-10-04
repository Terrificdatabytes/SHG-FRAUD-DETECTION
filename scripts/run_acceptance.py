#!/usr/bin/env python
"""Run all demo cases and fail if any verdict misses the documented expectation."""
from pathlib import Path
import json
import sys
import time

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core.config import load_config
from core.db import connect
from core.screening import load_bundle, screen_applicant


def allowed(expected: str) -> set[str]:
    return {item.strip() for item in expected.split("/")}


def main() -> int:
    config = load_config()
    manifest = json.loads((config.root / "demo_cases" / "manifest.json").read_text())
    connection = connect(config.db_path)
    bundle = load_bundle()
    rows = []
    try:
        for name, metadata in manifest.items():
            report = pd.read_csv(config.root / "demo_cases" / f"{name}.csv")
            started = time.perf_counter()
            result = screen_applicant(
                {
                    "consent": True,
                    "village": "Acceptance",
                    "shg_id": "SHG-DEMO",
                    "shg_age_months": 2 if name == "Applicant_I" else 12,
                    "amount": 50000,
                    "purpose": "Livelihood",
                    "is_demo": True,
                },
                report,
                connection,
                bundle,
            )
            elapsed = time.perf_counter() - started
            passed = result.verdict in allowed(metadata["expected_verdict"])
            rows.append(
                {
                    "case": name,
                    "truth": metadata["truth"],
                    "expected": metadata["expected_verdict"],
                    "actual": result.verdict,
                    "risk": round(result.risk, 4),
                    "ci": f"{result.ci_low:.3f}-{result.ci_high:.3f}",
                    "betti1": result.betti1,
                    "latency_s": round(elapsed, 3),
                    "status": "PASS" if passed else "FAIL",
                    "timings_ms": result.timings,
                }
            )
    finally:
        connection.close()
    printable = [{k: v for k, v in row.items() if k != "timings_ms"} for row in rows]
    print(pd.DataFrame(printable).to_string(index=False))
    (config.artifacts / "acceptance.json").write_text(json.dumps(rows, indent=2))
    failures = sum(row["status"] == "FAIL" for row in rows)
    print(f"\nAcceptance: {len(rows)-failures}/{len(rows)} passed; failures={failures}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
