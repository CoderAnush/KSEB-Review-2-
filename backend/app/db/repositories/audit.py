from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ApiBudgetLedger, AuditLog


class AuditRepo:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def append(self, actor: str, action: str, entity: str, entity_id: str, payload: dict) -> None:
        self.session.add(
            AuditLog(actor=actor, action=action, entity=entity, entity_id=entity_id, payload=payload)
        )
        await self.session.flush()

    async def list(self, limit: int = 200, offset: int = 0) -> list[dict]:
        stmt = select(AuditLog).order_by(AuditLog.id.desc()).limit(limit).offset(offset)
        rows = (await self.session.execute(stmt)).scalars().all()
        return [
            {
                "id": r.id,
                "ts": r.ts.isoformat() if r.ts else None,
                "actor": r.actor,
                "action": r.action,
                "entity": r.entity,
                "entity_id": r.entity_id,
                "payload": r.payload,
            }
            for r in rows
        ]


class BudgetRepo:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def add_entry(
        self,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cost_inr: float,
        pipeline_run_id: int | None = None,
    ) -> None:
        self.session.add(
            ApiBudgetLedger(
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_inr=cost_inr,
                pipeline_run_id=pipeline_run_id,
            )
        )
        await self.session.flush()

    async def month_spend_inr(self, year: int | None = None, month: int | None = None) -> float:
        now = datetime.now(timezone.utc)
        year = year or now.year
        month = month or now.month
        stmt = select(func.coalesce(func.sum(ApiBudgetLedger.cost_inr), 0.0)).where(
            extract("year", ApiBudgetLedger.ts) == year,
            extract("month", ApiBudgetLedger.ts) == month,
        )
        return float((await self.session.execute(stmt)).scalar_one())

    async def ledger(self, limit: int = 100) -> list[dict]:
        stmt = select(ApiBudgetLedger).order_by(ApiBudgetLedger.id.desc()).limit(limit)
        rows = (await self.session.execute(stmt)).scalars().all()
        return [
            {
                "id": r.id,
                "ts": r.ts.isoformat() if r.ts else None,
                "model": r.model,
                "input_tokens": r.input_tokens,
                "output_tokens": r.output_tokens,
                "cost_inr": r.cost_inr,
                "pipeline_run_id": r.pipeline_run_id,
            }
            for r in rows
        ]
