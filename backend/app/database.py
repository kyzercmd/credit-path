"""SQLAlchemy persistence layer supporting PostgreSQL and SQLite (B11)."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Generator

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    create_engine,
    desc,
    func,
    select,
)
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_config

DB_PATH = Path(__file__).resolve().parent.parent / "creditpath.db"

metadata = MetaData()

consent_log = Table(
    "consent_log",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("customer_id", String(64), nullable=False, index=True),
    Column("action", String(32), nullable=False),  # 'consent' or 'opt-out'
    Column("timestamp", String(64), nullable=False),
)

config_versions = Table(
    "config_versions",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("config_json", Text, nullable=False),
    Column("changed_by", String(64), nullable=False, default="system"),
    Column("timestamp", String(64), nullable=False),
)

kill_switch_log = Table(
    "kill_switch_log",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("state_json", Text, nullable=False),
    Column("changed_by", String(64), nullable=False, default="system"),
    Column("timestamp", String(64), nullable=False),
)

audit_log = Table(
    "audit_log",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("event_type", String(64), nullable=False),
    Column("details", Text, nullable=False),
    Column("timestamp", String(64), nullable=False),
)

funnel_events = Table(
    "funnel_events",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("customer_id", String(64), nullable=False, index=True),
    Column("stage", String(64), nullable=False, index=True),
    Column("metadata_json", Text, nullable=True),
    Column("timestamp", String(64), nullable=False),
)

live_transactions = Table(
    "live_transactions",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("customer_id", String(64), nullable=False, index=True),
    Column("date", String(32), nullable=False, index=True),
    Column("type", String(32), nullable=False),  # "inflow" or "outflow"
    Column("amount", Float, nullable=False),
    Column("description", String(256), nullable=True),
    Column("timestamp", String(64), nullable=False),
)

live_daily_balances = Table(
    "live_daily_balances",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("customer_id", String(64), nullable=False, index=True),
    Column("date", String(32), nullable=False, index=True),
    Column("balance", Float, nullable=False),
    Column("shortfall", Integer, nullable=False, default=0),
    Column("timestamp", String(64), nullable=False),
)

live_bills = Table(
    "live_bills",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("customer_id", String(64), nullable=False, index=True),
    Column("due_date", String(32), nullable=False, index=True),
    Column("amount", Float, nullable=False),
    Column("paid_date", String(32), nullable=True),
    Column("on_time", Integer, nullable=False, default=1),  # 1 for True, 0 for False
    Column("biller", String(128), nullable=True),
    Column("timestamp", String(64), nullable=False),
)

_engine: Engine | None = None
_session_factory: sessionmaker | None = None


def get_database_url() -> str:
    url = os.getenv("DATABASE_URL")
    if not url:
        try:
            url = get_config().database_url
        except Exception:
            url = f"sqlite:///{DB_PATH}"
    # Normalize postgres:// and postgresql:// scheme to postgresql+psycopg2://
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+psycopg2://", 1)
    elif url.startswith("postgresql://") and not url.startswith("postgresql+"):
        url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
    return url


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        db_url = get_database_url()
        connect_args = {}
        if db_url.startswith("sqlite"):
            connect_args = {"timeout": 15.0}
        _engine = create_engine(
            db_url,
            connect_args=connect_args,
            pool_pre_ping=True,
            future=True,
        )
    return _engine


def get_session_factory() -> sessionmaker:
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(bind=get_engine(), expire_on_commit=False, future=True)
    return _session_factory


def reset_engine() -> None:
    """Useful in tests when switching between sqlite and postgres URLs."""
    global _engine, _session_factory
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _session_factory = None


def init_db() -> None:
    engine = get_engine()
    metadata.create_all(engine)

    SessionLocal = get_session_factory()
    with SessionLocal() as session:
        count_stmt = select(func.count()).select_from(config_versions)
        cnt = session.execute(count_stmt).scalar() or 0
        if cnt == 0:
            from app.config import get_config

            now = datetime.now(timezone.utc).isoformat()
            insert_stmt = config_versions.insert().values(
                config_json=json.dumps(get_config().to_dict()),
                changed_by="system",
                timestamp=now,
            )
            session.execute(insert_stmt)
            session.commit()


def log_audit(event_type: str, details: str) -> None:
    SessionLocal = get_session_factory()
    with SessionLocal() as session:
        session.execute(
            audit_log.insert().values(
                event_type=event_type,
                details=details,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
        )
        session.commit()


def log_consent(customer_id: str, action: str) -> None:
    SessionLocal = get_session_factory()
    now = datetime.now(timezone.utc).isoformat()
    with SessionLocal() as session:
        session.execute(
            consent_log.insert().values(
                customer_id=customer_id,
                action=action,
                timestamp=now,
            )
        )
        session.commit()
    log_audit("consent", json.dumps({"customer_id": customer_id, "action": action}))


def save_config_version(config_dict: dict, changed_by: str = "system") -> None:
    SessionLocal = get_session_factory()
    now = datetime.now(timezone.utc).isoformat()
    with SessionLocal() as session:
        session.execute(
            config_versions.insert().values(
                config_json=json.dumps(config_dict),
                changed_by=changed_by,
                timestamp=now,
            )
        )
        session.commit()
    log_audit("config_change", json.dumps({"changed_by": changed_by}))


def save_kill_switch(state: dict, changed_by: str = "system") -> None:
    SessionLocal = get_session_factory()
    now = datetime.now(timezone.utc).isoformat()
    with SessionLocal() as session:
        session.execute(
            kill_switch_log.insert().values(
                state_json=json.dumps(state),
                changed_by=changed_by,
                timestamp=now,
            )
        )
        session.commit()
    log_audit("kill_switch", json.dumps({"changed_by": changed_by, "state": state}))


def get_audit_log() -> list[dict]:
    SessionLocal = get_session_factory()
    with SessionLocal() as session:
        stmt = (
            select(audit_log.c.event_type, audit_log.c.details, audit_log.c.timestamp)
            .order_by(desc(audit_log.c.id))
            .limit(200)
        )
        rows = session.execute(stmt).fetchall()
        return [
            {"event_type": r[0], "details": r[1], "timestamp": r[2]}
            for r in rows
        ]


def get_consent_status(customer_id: str) -> str | None:
    SessionLocal = get_session_factory()
    with SessionLocal() as session:
        stmt = (
            select(consent_log.c.action)
            .where(consent_log.c.customer_id == customer_id)
            .order_by(desc(consent_log.c.id))
            .limit(1)
        )
        row = session.execute(stmt).fetchone()
        return row[0] if row else None


def get_latest_config_version() -> tuple[int, str]:
    SessionLocal = get_session_factory()
    with SessionLocal() as session:
        stmt = (
            select(config_versions.c.id, config_versions.c.timestamp)
            .order_by(desc(config_versions.c.id))
            .limit(1)
        )
        row = session.execute(stmt).fetchone()
        if row:
            return int(row[0]), str(row[1])
        return 1, datetime.now(timezone.utc).isoformat()


def log_funnel_event(customer_id: str, stage: str, metadata_dict: dict | None = None) -> None:
    SessionLocal = get_session_factory()
    now = datetime.now(timezone.utc).isoformat()
    meta_json = json.dumps(metadata_dict) if metadata_dict else None
    with SessionLocal() as session:
        session.execute(
            funnel_events.insert().values(
                customer_id=customer_id,
                stage=stage,
                metadata_json=meta_json,
                timestamp=now,
            )
        )
        session.commit()


def get_funnel_analytics() -> dict[str, Any]:
    SessionLocal = get_session_factory()
    with SessionLocal() as session:
        # Count distinct customers per stage
        stmt = (
            select(funnel_events.c.stage, func.count(func.distinct(funnel_events.c.customer_id)))
            .group_by(funnel_events.c.stage)
        )
        rows = session.execute(stmt).fetchall()
        counts_by_stage = {r[0]: int(r[1]) for r in rows}

        total_unique_stmt = select(func.count(func.distinct(funnel_events.c.customer_id))).select_from(funnel_events)
        total_unique = int(session.execute(total_unique_stmt).scalar() or 0)

        standard_stages = [
            "profile_viewed",
            "path_explored",
            "action_plan_committed",
            "loan_check_performed",
            "credit_converted",
        ]

        conversion_rates = {}
        prev_count = total_unique
        for stage in standard_stages:
            cnt = counts_by_stage.get(stage, 0)
            step_rate = (cnt / prev_count * 100.0) if prev_count > 0 else 0.0
            overall_rate = (cnt / total_unique * 100.0) if total_unique > 0 else 0.0
            conversion_rates[stage] = {
                "unique_users": cnt,
                "step_conversion_pct": round(step_rate, 2),
                "overall_conversion_pct": round(overall_rate, 2),
            }
            prev_count = cnt if cnt > 0 else prev_count

        return {
            "total_tracked_users": total_unique,
            "stages": conversion_rates,
            "counts_by_stage": counts_by_stage,
        }


def insert_live_transaction(customer_id: str, date: str, tx_type: str, amount: float, description: str | None = None) -> dict[str, Any]:
    SessionLocal = get_session_factory()
    now = datetime.now(timezone.utc).isoformat()
    with SessionLocal() as session:
        result = session.execute(
            live_transactions.insert().values(
                customer_id=customer_id,
                date=date,
                type=tx_type,
                amount=amount,
                description=description,
                timestamp=now,
            )
        )
        session.commit()
    return {
        "customer_id": customer_id,
        "date": date,
        "type": tx_type,
        "amount": amount,
        "description": description,
        "timestamp": now,
    }


def insert_live_daily_balance(customer_id: str, date: str, balance: float, shortfall: int = 0) -> dict[str, Any]:
    SessionLocal = get_session_factory()
    now = datetime.now(timezone.utc).isoformat()
    with SessionLocal() as session:
        session.execute(
            live_daily_balances.insert().values(
                customer_id=customer_id,
                date=date,
                balance=balance,
                shortfall=shortfall,
                timestamp=now,
            )
        )
        session.commit()
    return {
        "customer_id": customer_id,
        "date": date,
        "balance": balance,
        "shortfall": shortfall,
        "timestamp": now,
    }


def insert_live_bill(customer_id: str, due_date: str, amount: float, paid_date: str | None = None, on_time: int = 1, biller: str | None = None) -> dict[str, Any]:
    SessionLocal = get_session_factory()
    now = datetime.now(timezone.utc).isoformat()
    with SessionLocal() as session:
        session.execute(
            live_bills.insert().values(
                customer_id=customer_id,
                due_date=due_date,
                amount=amount,
                paid_date=paid_date,
                on_time=on_time,
                biller=biller,
                timestamp=now,
            )
        )
        session.commit()
    return {
        "customer_id": customer_id,
        "due_date": due_date,
        "amount": amount,
        "paid_date": paid_date,
        "on_time": on_time,
        "biller": biller,
        "timestamp": now,
    }


def get_live_transactions(customer_id: str | None = None) -> list[dict[str, Any]]:
    SessionLocal = get_session_factory()
    with SessionLocal() as session:
        stmt = select(
            live_transactions.c.customer_id,
            live_transactions.c.date,
            live_transactions.c.type,
            live_transactions.c.amount,
            live_transactions.c.description,
            live_transactions.c.timestamp,
        )
        if customer_id:
            stmt = stmt.where(live_transactions.c.customer_id == customer_id)
        stmt = stmt.order_by(live_transactions.c.date.asc())
        rows = session.execute(stmt).fetchall()
        return [
            {
                "customer_id": r[0],
                "date": r[1],
                "type": r[2],
                "amount": float(r[3]),
                "description": r[4],
                "timestamp": r[5],
            }
            for r in rows
        ]


def get_live_daily_balances(customer_id: str | None = None) -> list[dict[str, Any]]:
    SessionLocal = get_session_factory()
    with SessionLocal() as session:
        stmt = select(
            live_daily_balances.c.customer_id,
            live_daily_balances.c.date,
            live_daily_balances.c.balance,
            live_daily_balances.c.shortfall,
            live_daily_balances.c.timestamp,
        )
        if customer_id:
            stmt = stmt.where(live_daily_balances.c.customer_id == customer_id)
        stmt = stmt.order_by(live_daily_balances.c.date.asc())
        rows = session.execute(stmt).fetchall()
        return [
            {
                "customer_id": r[0],
                "date": r[1],
                "balance": float(r[2]),
                "shortfall": int(r[3]),
                "timestamp": r[4],
            }
            for r in rows
        ]


def get_live_bills(customer_id: str | None = None) -> list[dict[str, Any]]:
    SessionLocal = get_session_factory()
    with SessionLocal() as session:
        stmt = select(
            live_bills.c.customer_id,
            live_bills.c.due_date,
            live_bills.c.amount,
            live_bills.c.paid_date,
            live_bills.c.on_time,
            live_bills.c.biller,
            live_bills.c.timestamp,
        )
        if customer_id:
            stmt = stmt.where(live_bills.c.customer_id == customer_id)
        stmt = stmt.order_by(live_bills.c.due_date.asc())
        rows = session.execute(stmt).fetchall()
        return [
            {
                "customer_id": r[0],
                "due_date": r[1],
                "amount": float(r[2]),
                "paid_date": r[3],
                "on_time": int(r[4]),
                "biller": r[5],
                "timestamp": r[6],
            }
            for r in rows
        ]

