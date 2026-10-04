"""Privacy-preserving applicant screening with a topology-feature MLP."""
from __future__ import annotations

from dataclasses import dataclass
import json
import time
import uuid

import numpy as np
import pandas as pd
import torch

from .config import load_config
from .db import audit
from .explain import explain
from .features import FEATURE_NAMES, report_features
from .ingest import validate_report
from .model import TopologyMLP
from .privacy import hash_identifier
from .scaling import load_scaler, transform
from .tda import BACKEND, report_topology
from .train import TDA_COLUMNS
from .uncertainty import mc_predict


@dataclass
class ScreenResult:
    app_id: str
    node_id: str
    risk: float
    ci_low: float
    ci_high: float
    verdict: str
    hist_months: float
    betti1: int
    loop_nodes: list
    hub: str
    top_edges: list
    explanation_text: str
    features_top: list
    timings: dict
    backend: str
    warnings: list
    persistence: list
    report: list


def load_bundle() -> dict:
    config = load_config()
    checkpoint = torch.load(config.artifacts / "model.pt", map_location="cpu", weights_only=True)
    model = TopologyMLP(checkpoint["input_dim"], hidden=checkpoint["hidden"])
    model.load_state_dict(checkpoint["state"])
    scaler = load_scaler(config.artifacts / "scaler.json")
    topology_scaler = load_scaler(config.artifacts / "topology_scaler.json")
    return {
        "model": model,
        "scaler": scaler,
        "topology_scaler": topology_scaler,
        "thresholds": json.loads((config.artifacts / "thresholds.json").read_text()),
        "input_columns": checkpoint["input_columns"],
    }


def _timed(timings: dict, name: str, started: float) -> None:
    timings[name] = round((time.perf_counter() - started) * 1000, 2)


def _domain_warnings(form: dict, report: pd.DataFrame) -> list[str]:
    domain = load_config().domain
    warnings = []
    age = form.get("age")
    if age is not None and not domain["age_min"] <= int(age) <= domain["age_max"]:
        warnings.append(
            f"Applicant age must be {domain['age_min']}–{domain['age_max']} years"
        )
    group_size = form.get("group_size")
    if group_size is not None and not domain["normal_group_min"] <= int(group_size) <= domain["normal_group_max"]:
        warnings.append(
            f"Normal SHG size is {domain['normal_group_min']}–{domain['normal_group_max']}"
        )
    if float(form.get("shg_age_months", 12)) < domain["grading_months"]:
        warnings.append("SHG is ungraded because its history is under six months")
    savings = report[report["narration"].str.contains("saving", case=False, na=False)]
    if not savings.empty and savings["amount"].median() < domain["monthly_saving_min"]:
        warnings.append(
            f"Median monthly saving is below the ₹{domain['monthly_saving_min']} programme assumption"
        )
    return warnings


def _hash_report(report: pd.DataFrame) -> pd.DataFrame:
    hashed = report.copy()
    hashed["account_id"] = hashed["account_id"].map(hash_identifier)
    hashed["counterparty_id"] = hashed["counterparty_id"].map(hash_identifier)
    return hashed


def _persist_overlay(connection, form: dict, report: pd.DataFrame, node_id: str, now: int) -> None:
    connection.execute(
        "INSERT OR IGNORE INTO nodes VALUES(?,?,?,?,?,?,?,?,?,?)",
        (
            node_id,
            "member",
            form.get("village", ""),
            form.get("shg_id", "New SHG"),
            form.get("plf_id", ""),
            None,
            int(float(form.get("shg_age_months", 12)) >= load_config().domain["grading_months"]),
            0,
            now,
            "pending",
        ),
    )
    for field in ("name", "mobile"):
        if form.get(field):
            identifier = hash_identifier(form[field])
            connection.execute(
                "INSERT OR IGNORE INTO nodes VALUES(?,?,?,?,?,?,?,?,?,?)",
                (identifier, "identifier", "", None, None, None, 0, 0, now, "pending"),
            )
            connection.execute(
                "INSERT OR IGNORE INTO edges VALUES(?,?,?,?,?,?,?)",
                (node_id, identifier, "shared_id", 0.0, now, f"ID-{field}-{identifier[:12]}", "pending"),
            )
    for _, row in report.iterrows():
        counterparty = str(row["counterparty_id"])
        connection.execute(
            "INSERT OR IGNORE INTO nodes VALUES(?,?,?,?,?,?,?,?,?,?)",
            (counterparty, "external", "", None, None, None, 0, 0, now, "pending"),
        )
        source, destination = (
            (counterparty, node_id) if row["direction"] == "CR" else (node_id, counterparty)
        )
        connection.execute(
            "INSERT OR IGNORE INTO edges VALUES(?,?,?,?,?,?,?)",
            (
                source,
                destination,
                "transfer",
                float(row["amount"]),
                int(row["date"].timestamp()),
                str(row["txn_id"]),
                "pending",
            ),
        )


def _score(bundle: dict, features: dict, topology: np.ndarray) -> tuple[float, float, float]:
    torch.manual_seed(load_config().seed)
    scaled = transform(pd.DataFrame([features]), bundle["scaler"])
    topology_frame = pd.DataFrame([topology], columns=TDA_COLUMNS)
    scaled_topology = transform(topology_frame, bundle["topology_scaler"])
    combined = np.column_stack([scaled, scaled_topology])
    tensor = torch.tensor(combined, dtype=torch.float32)
    mean, low, high, _ = mc_predict(
        bundle["model"], tensor, load_config().model["mc_samples"], features["history_months"]
    )
    return float(mean[0]), float(low[0]), float(high[0])


def _verdict(risk: float, low: float, high: float, history: float, thresholds: dict) -> str:
    if risk >= thresholds["t_high"]:
        return "HIGH"
    if (
        risk >= thresholds["t_low"]
        or high - low > 0.35
        or history < 3
    ):
        return "REVIEW"
    return "LOW"


def screen_applicant(form, df_report, connection, model_bundle=None) -> ScreenResult:
    """Run the same trained screening path for uploaded and sample reports."""
    timings: dict[str, float] = {}
    started = time.perf_counter()
    validation = validate_report(df_report, hash_ids=False)
    if validation.errors:
        raise ValueError("; ".join(validation.errors))
    if not form.get("consent"):
        raise ValueError("Applicant consent is required")
    warnings = validation.warnings + _domain_warnings(form, validation.data)
    _timed(timings, "Validate", started)

    started = time.perf_counter()
    report = _hash_report(validation.data)
    node_id = str(report["account_id"].iloc[0])
    _timed(timings, "Hash identifiers", started)

    app_id = "APP-" + uuid.uuid4().hex[:10].upper()
    now = int(time.time())
    started = time.perf_counter()
    _persist_overlay(connection, form, report, node_id, now)
    _timed(timings, "Build graph overlay", started)

    started = time.perf_counter()
    features = report_features(report)
    topology, loop, intervals, _, _ = report_topology(report)
    _timed(timings, "Cycle topology & features", started)

    started = time.perf_counter()
    bundle = model_bundle or load_bundle()
    risk, ci_low, ci_high = _score(bundle, features, topology)
    verdict = _verdict(
        risk,
        ci_low,
        ci_high,
        features["history_months"],
        bundle["thresholds"],
    )
    _timed(timings, "MLP scoring", started)

    started = time.perf_counter()
    top_edges, hub, explanation, _ = explain(
        report, features, risk, ci_low, ci_high, loop
    )
    _timed(timings, "Explain", started)

    started = time.perf_counter()
    connection.execute("DELETE FROM scores WHERE node_id=?", (node_id,))
    connection.execute(
        "INSERT INTO scores VALUES(?,?,?,?,?,?,?,?,?)",
        (
            node_id,
            risk,
            ci_low,
            ci_high,
            int(topology[1]),
            verdict,
            features["history_months"],
            "topology-mlp-2.0",
            now,
        ),
    )
    connection.execute(
        "INSERT INTO applications VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            app_id,
            node_id,
            form.get("shg_id", "New SHG"),
            form.get("village", ""),
            float(form.get("amount", 0)),
            form.get("purpose", ""),
            1,
            now,
            verdict,
            risk,
            ci_low,
            ci_high,
            None,
            None,
            None,
            int(bool(form.get("is_demo", False))),
        ),
    )
    if verdict != "LOW":
        connection.execute(
            "INSERT INTO alerts(node_id,app_id,level,summary,created_ts) VALUES(?,?,?,?,?)",
            (node_id, app_id, verdict, explanation, now),
        )
    connection.execute(
        "INSERT OR REPLACE INTO explanations VALUES(?,?,?,?)",
        (node_id, json.dumps(top_edges), explanation, now),
    )
    audit(connection, "SCREEN", f"{app_id} verdict={verdict} risk={risk:.4f}")
    connection.commit()
    _timed(timings, "Persist", started)

    feature_top = sorted(
        ({"feature": key, "value": float(value)} for key, value in features.items()),
        key=lambda item: abs(item["value"]),
        reverse=True,
    )[:8]
    safe_report = report.assign(
        account_id="Applicant", counterparty_id=report["counterparty_id"].str[:8]
    ).to_dict("records")
    for row in safe_report:
        row["date"] = str(row["date"])
    return ScreenResult(
        app_id,
        node_id,
        risk,
        ci_low,
        ci_high,
        verdict,
        float(features["history_months"]),
        int(topology[1]),
        loop,
        hub,
        top_edges,
        explanation,
        feature_top,
        timings,
        BACKEND,
        warnings,
        [(float(birth), float(death)) for birth, death in intervals],
        safe_report,
    )


def record_decision(
    connection,
    app_id: str,
    verdict: str,
    decision: str,
    reason: str,
    actor: str,
) -> None:
    row = connection.execute(
        "SELECT verdict,decision FROM applications WHERE app_id=?", (app_id,)
    ).fetchone()
    if row is None:
        raise ValueError("Unknown application")
    if row["decision"] is not None:
        raise ValueError("A decision has already been recorded")
    if decision in {"Hold", "Reject"} and len(reason.strip()) < 5:
        raise ValueError("Hold and Reject require a reason of at least 5 characters")
    if decision == "Approve" and row["verdict"] != "LOW" and len(reason.strip()) < 15:
        raise ValueError("Flagged approval requires an override reason of at least 15 characters")
    if not actor.strip():
        raise ValueError("Officer identity is required")
    now = int(time.time())
    connection.execute(
        "UPDATE applications SET decision=?,decision_reason=?,decided_ts=? WHERE app_id=?",
        (decision, reason.strip(), now, app_id),
    )
    audit(connection, "DECISION", f"{app_id} {decision}: {reason.strip()}", actor.strip())
    connection.commit()
