"""SQLite schema, migrations, and chained audit helpers."""
from __future__ import annotations

import hashlib
import sqlite3
import time
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS nodes(
 id TEXT PRIMARY KEY, ntype TEXT, village TEXT, shg_id TEXT, plf_id TEXT,
 family_id TEXT, graded INTEGER, special_shg INTEGER, created_ts INTEGER,
 status TEXT DEFAULT 'active');
CREATE TABLE IF NOT EXISTS edges(
 src TEXT,dst TEXT,etype TEXT,amount REAL,ts INTEGER,txn_id TEXT,
 status TEXT DEFAULT 'active');
CREATE INDEX IF NOT EXISTS idx_edges_src ON edges(src);
CREATE INDEX IF NOT EXISTS idx_edges_dst ON edges(dst);
CREATE UNIQUE INDEX IF NOT EXISTS idx_edge_txn ON edges(src,dst,txn_id,status);
CREATE TABLE IF NOT EXISTS labels(
 node_id TEXT PRIMARY KEY,y_member INTEGER,y_shadow INTEGER,split TEXT,pattern TEXT);
CREATE TABLE IF NOT EXISTS node_features(
 node_id TEXT PRIMARY KEY,vec BLOB,tda BLOB,updated_ts INTEGER);
CREATE TABLE IF NOT EXISTS scores(
 node_id TEXT,risk REAL,ci_low REAL,ci_high REAL,betti1 INTEGER,
 verdict TEXT,hist_months REAL,model_ver TEXT,scored_ts INTEGER);
CREATE TABLE IF NOT EXISTS applications(
 app_id TEXT PRIMARY KEY,node_id TEXT,shg_id TEXT,village TEXT,amount REAL,
 purpose TEXT,consent INTEGER,created_ts INTEGER,verdict TEXT,risk REAL,
 ci_low REAL,ci_high REAL,decision TEXT,decision_reason TEXT,decided_ts INTEGER,
 is_demo INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS alerts(
 alert_id INTEGER PRIMARY KEY AUTOINCREMENT,node_id TEXT,app_id TEXT,level TEXT,
 summary TEXT,created_ts INTEGER,status TEXT DEFAULT 'open');
CREATE TABLE IF NOT EXISTS explanations(
 node_id TEXT PRIMARY KEY,top_edges TEXT,text TEXT,created_ts INTEGER);
CREATE TABLE IF NOT EXISTS audit_log(
 id INTEGER PRIMARY KEY AUTOINCREMENT,ts INTEGER,actor TEXT,action TEXT,
 detail TEXT,prev_hash TEXT,row_hash TEXT);
"""


def connect(path: str | Path) -> sqlite3.Connection:
    Path(path).parent.mkdir(parents=True, exist_ok=True) if str(path) != ":memory:" else None
    connection = sqlite3.connect(path, timeout=20, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA journal_mode=WAL")
    connection.execute("PRAGMA foreign_keys=ON")
    connection.executescript(SCHEMA)
    columns = {row[1] for row in connection.execute("PRAGMA table_info(applications)")}
    if "is_demo" not in columns:
        connection.execute("ALTER TABLE applications ADD COLUMN is_demo INTEGER DEFAULT 0")
        connection.commit()
    return connection


def _audit_digest(ts: int, actor: str, action: str, detail: str, previous: str) -> str:
    payload = f"{ts}|{actor}|{action}|{detail}|{previous}".encode()
    return hashlib.sha256(payload).hexdigest()


def audit(connection, action: str, detail: str, actor: str = "officer") -> str:
    previous_row = connection.execute(
        "SELECT row_hash FROM audit_log ORDER BY id DESC LIMIT 1"
    ).fetchone()
    previous = previous_row[0] if previous_row else "GENESIS"
    timestamp = int(time.time())
    row_hash = _audit_digest(timestamp, actor, action, detail, previous)
    connection.execute(
        "INSERT INTO audit_log(ts,actor,action,detail,prev_hash,row_hash) "
        "VALUES(?,?,?,?,?,?)",
        (timestamp, actor, action, detail, previous, row_hash),
    )
    return row_hash


def verify_audit_chain(connection) -> bool:
    previous = "GENESIS"
    for row in connection.execute("SELECT * FROM audit_log ORDER BY id"):
        expected = _audit_digest(
            int(row["ts"]), row["actor"], row["action"], row["detail"], previous
        )
        if row["prev_hash"] != previous or row["row_hash"] != expected:
            return False
        previous = row["row_hash"]
    return True


def init_db(path: str | Path) -> None:
    connection = connect(path)
    connection.close()
