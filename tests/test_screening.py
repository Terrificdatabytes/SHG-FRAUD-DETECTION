import sqlite3
import time

import pandas as pd
import pytest

from core.config import load_config
from core.db import connect, verify_audit_chain
from core.screening import load_bundle, record_decision, screen_applicant


def form(**updates):
    base = {
        "consent": True,
        "village": "V",
        "shg_id": "S",
        "shg_age_months": 12,
        "amount": 50000,
        "purpose": "test",
        "name": "Raw Person Name",
        "mobile": "9876543210",
    }
    base.update(updates)
    return base


def test_clean_and_fraud_screen_under_budget():
    config = load_config()
    database = connect(":memory:")
    bundle = load_bundle()
    started = time.perf_counter()
    clean = screen_applicant(
        form(), pd.read_csv(config.root / "demo_cases/Applicant_A.csv"), database, bundle
    )
    fraud = screen_applicant(
        form(name="Other Name", mobile="9123456780"),
        pd.read_csv(config.root / "demo_cases/Applicant_E.csv"),
        database,
        bundle,
    )
    assert clean.verdict == "LOW"
    assert fraud.verdict in {"REVIEW", "HIGH"}
    assert time.perf_counter() - started < 5
    dump = "\n".join(database.iterdump())
    assert "Raw Person Name" not in dump
    assert "9876543210" not in dump
    assert verify_audit_chain(database)


def test_decision_rules_and_unknown_application():
    config = load_config()
    database = connect(":memory:")
    result = screen_applicant(
        form(), pd.read_csv(config.root / "demo_cases/Applicant_E.csv"), database, load_bundle()
    )
    with pytest.raises(ValueError, match="override"):
        record_decision(database, result.app_id, result.verdict, "Approve", "short", "officer-1")
    with pytest.raises(ValueError, match="Unknown"):
        record_decision(database, "missing", "HIGH", "Hold", "reason", "officer-1")
    record_decision(
        database,
        result.app_id,
        result.verdict,
        "Approve",
        "Verified after a field visit",
        "officer-1",
    )
    with pytest.raises(ValueError, match="already"):
        record_decision(database, result.app_id, result.verdict, "Hold", "reason", "officer-1")
    assert verify_audit_chain(database)
