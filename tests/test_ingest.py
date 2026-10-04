import pandas as pd

from core.ingest import validate_report


def valid_frame():
    return pd.DataFrame(
        {
            "date": ["2026-01-01"] * 5,
            "txn_id": range(5),
            "account_id": ["a"] * 5,
            "counterparty_id": ["b"] * 5,
            "direction": ["dr", "CR", "DR", "CR", "DR"],
            "amount": [1, 2, 3, 4, 5],
            "channel": ["UPI"] * 5,
            "narration": ["x"] * 5,
        }
    )


def test_mixed_case_direction_is_normalized():
    result = validate_report(valid_frame())
    assert not result.errors
    assert set(result.data.direction) == {"CR", "DR"}


def test_hostile_reports_have_clear_errors():
    short = valid_frame().iloc[:4]
    assert any("at least 5" in error for error in validate_report(short).errors)
    missing = valid_frame().drop(columns=["amount"])
    assert any("amount" in error for error in validate_report(missing).errors)
    bad = valid_frame()
    bad.loc[1, "amount"] = float("nan")
    bad.loc[2, "channel"] = "UNKNOWN"
    errors = validate_report(bad).errors
    assert any("amount must be positive" in error for error in errors)
    assert any("unsupported channel" in error for error in errors)
