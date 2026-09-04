from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ApprovalRow, RecommendationRow, RiskAlertRow, ThumbRuleRow
from app.domain.entities import ApprovalRecord, Recommendation, RiskAlert, ThumbRule
from app.domain.enums import AlertSeverity, ApprovalDecision, RecommendationStatus, ScheduleSource


class AlreadyDecidedError(RuntimeError):
    """A second approval/rejection was attempted for the same recommendation."""


def _to_entity(row: RecommendationRow) -> Recommendation:
    return Recommendation(
        day=row.day,
        rank=row.rank,
        title=row.title,
        action_summary=row.action_summary,
        expected_cost_inr=row.expected_cost_inr,
        expected_savings_inr=row.expected_savings_inr,
        savings_vs_baseline_pct=row.savings_vs_baseline_pct,
        risk_score=row.risk_score,
        robustness_score=row.robustness_score,
        composite_score=row.composite_score,
        schedule_source=ScheduleSource(row.schedule_source),
        narrative=row.narrative,
        payload=row.payload,
        status=RecommendationStatus(row.status),
    )


class RecommendationsRepo:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def save_recommendations(
        self, pipeline_run_id: int | None, recs: list[Recommendation]
    ) -> list[int]:
        ids: list[int] = []
        for r in recs:
            row = RecommendationRow(
                pipeline_run_id=pipeline_run_id,
                day=r.day,
                rank=r.rank,
                title=r.title,
                action_summary=r.action_summary,
                expected_cost_inr=r.expected_cost_inr,
                expected_savings_inr=r.expected_savings_inr,
                savings_vs_baseline_pct=r.savings_vs_baseline_pct,
                risk_score=r.risk_score,
                robustness_score=r.robustness_score,
                composite_score=r.composite_score,
                schedule_source=r.schedule_source.value,
                narrative=r.narrative,
                payload=r.payload,
                status=r.status.value,
            )
            self.session.add(row)
            await self.session.flush()
            ids.append(row.id)
        return ids

    async def list_for_day(self, day: date) -> list[tuple[int, Recommendation]]:
        stmt = (
            select(RecommendationRow)
            .where(RecommendationRow.day == day)
            .order_by(RecommendationRow.id.desc())
        )
        rows = (await self.session.execute(stmt)).scalars().all()
        # newest pipeline run only
        newest = rows[0].pipeline_run_id if rows else None
        picked = [r for r in rows if r.pipeline_run_id == newest]
        picked.sort(key=lambda r: r.rank)
        return [(r.id, _to_entity(r)) for r in picked]

    async def get(self, rec_id: int) -> tuple[int, Recommendation] | None:
        row = await self.session.get(RecommendationRow, rec_id)
        return (row.id, _to_entity(row)) if row else None

    async def set_status(self, rec_id: int, status: RecommendationStatus) -> None:
        row = await self.session.get(RecommendationRow, rec_id)
        if row is not None:
            row.status = status.value

    async def any_approved_for_day(self, day: date) -> bool:
        """True iff the newest pipeline run's recommendations for `day` include an
        approved one — the gate the bid-CSV export (execution boundary, A10) checks."""
        recs = await self.list_for_day(day)
        return any(r.status == RecommendationStatus.APPROVED for _, r in recs)

    async def save_alerts(self, pipeline_run_id: int | None, alerts: list[RiskAlert]) -> None:
        # alerts carry no day; derive from linked run's recommendations context is
        # unnecessary — store with the run id and let the API filter through runs.
        for a in alerts:
            self.session.add(
                RiskAlertRow(
                    pipeline_run_id=pipeline_run_id,
                    day=getattr(a, "day", None) or date.today(),
                    severity=a.severity.value,
                    kind=a.kind,
                    message=a.message,
                    from_block=a.from_block,
                    to_block=a.to_block,
                )
            )
        await self.session.flush()

    async def save_alerts_for_day(
        self, pipeline_run_id: int | None, day: date, alerts: list[RiskAlert]
    ) -> None:
        for a in alerts:
            self.session.add(
                RiskAlertRow(
                    pipeline_run_id=pipeline_run_id,
                    day=day,
                    severity=a.severity.value,
                    kind=a.kind,
                    message=a.message,
                    from_block=a.from_block,
                    to_block=a.to_block,
                )
            )
        await self.session.flush()

    async def list_alerts(self, day: date) -> list[RiskAlert]:
        stmt = select(RiskAlertRow).where(RiskAlertRow.day == day).order_by(RiskAlertRow.id)
        rows = (await self.session.execute(stmt)).scalars().all()
        return [
            RiskAlert(
                severity=AlertSeverity(r.severity),
                kind=r.kind,
                message=r.message,
                from_block=r.from_block,
                to_block=r.to_block,
            )
            for r in rows
        ]

    async def save_thumb_rules(
        self, pipeline_run_id: int | None, rules: list[ThumbRule], day: date | None = None
    ) -> None:
        for t in rules:
            self.session.add(
                ThumbRuleRow(pipeline_run_id=pipeline_run_id, day=day, text=t.text, evidence=t.evidence)
            )
        await self.session.flush()

    async def create_approval(self, rec_id: int, decision: ApprovalDecision, note: str, username: str) -> int:
        if not note or not note.strip():
            raise ValueError("approval note is mandatory")
        existing = await self.approval_for(rec_id)
        if existing is not None:
            raise AlreadyDecidedError(f"recommendation {rec_id} already decided")
        row = ApprovalRow(
            recommendation_id=rec_id, decision=decision.value, note=note.strip(), username=username
        )
        self.session.add(row)
        try:
            await self.session.flush()
        except IntegrityError as exc:
            # TOCTOU (W2): a concurrent decision passed the check-then-insert window
            # and hit the unique constraint first. Immutability holds — the DB won —
            # so translate the race into the same 409 as a sequential double-decision
            # rather than leaking a 500. The unique constraint is the real backstop.
            # No rollback here (I15): the request's session_scope rolls back on this
            # raised error; the boundary owns commit/rollback, repos only flush.
            raise AlreadyDecidedError(f"recommendation {rec_id} already decided") from exc
        return row.id

    async def approval_for(self, rec_id: int) -> ApprovalRecord | None:
        stmt = select(ApprovalRow).where(ApprovalRow.recommendation_id == rec_id)
        row = (await self.session.execute(stmt)).scalars().first()
        if row is None:
            return None
        return ApprovalRecord(
            recommendation_id=row.recommendation_id,
            decision=ApprovalDecision(row.decision),
            note=row.note,
            username=row.username,
            decided_at=row.decided_at,
        )
