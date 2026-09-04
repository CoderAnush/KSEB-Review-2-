from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    EnvelopeRow,
    Forecast,
    ForecastMetric,
    MilpRun,
    PipelineRun,
    ScheduleBlockRow,
    TwinKpi,
    TwinValidation,
)
from app.domain.entities import (
    DispatchBlock,
    DispatchSchedule,
    Envelope,
    EnvelopeBlock,
    ForecastMetrics,
    ForecastSet,
    GateResult,
    ScenarioResult,
    SolverStats,
    TwinKPIs,
    ValidationReport,
)
from app.domain.enums import ForecastTarget, PipelineStage, RunStatus, ScheduleSource


class RunsRepo:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ------------------------------------------------------------- pipeline runs
    async def create_pipeline_run(
        self, stage: PipelineStage, day: date, config_versions: dict[str, str]
    ) -> int:
        run = PipelineRun(
            stage=stage.value, day=day, status=RunStatus.RUNNING.value, config_versions=config_versions
        )
        self.session.add(run)
        await self.session.flush()
        return run.id

    async def finish_pipeline_run(self, run_id: int, status: RunStatus, detail: str = "") -> None:
        run = await self.session.get(PipelineRun, run_id)
        if run is None:
            return
        run.status = status.value
        run.detail = detail
        run.finished_at = datetime.now(timezone.utc)

    async def list_runs(self, day: date | None = None, limit: int = 50) -> list[dict]:
        stmt = select(PipelineRun).order_by(PipelineRun.id.desc()).limit(limit)
        if day is not None:
            stmt = stmt.where(PipelineRun.day == day)
        rows = (await self.session.execute(stmt)).scalars().all()
        return [
            {
                "id": r.id,
                "stage": r.stage,
                "day": r.day.isoformat(),
                "status": r.status,
                "detail": r.detail,
                "config_versions": r.config_versions,
                "started_at": r.started_at.isoformat() if r.started_at else None,
                "finished_at": r.finished_at.isoformat() if r.finished_at else None,
            }
            for r in rows
        ]

    # ------------------------------------------------------------- forecasts
    async def save_forecast(self, pipeline_run_id: int | None, fs: ForecastSet) -> None:
        for label, values in fs.quantiles.items():
            self.session.add(
                Forecast(
                    pipeline_run_id=pipeline_run_id,
                    target=fs.target.value,
                    day=fs.day,
                    quantile=label,
                    values=list(values),
                    model_name=fs.model_name,
                    model_version=fs.model_version,
                )
            )
        await self.session.flush()

    async def latest_forecast(self, target: ForecastTarget, day: date) -> ForecastSet | None:
        stmt = (
            select(Forecast)
            .where(Forecast.target == target.value, Forecast.day == day)
            .order_by(Forecast.id.desc())
        )
        rows = (await self.session.execute(stmt)).scalars().all()
        if not rows:
            return None
        newest_run = rows[0].pipeline_run_id
        quantiles: dict[str, list[float]] = {}
        model_name = rows[0].model_name
        model_version = rows[0].model_version
        for r in rows:
            if r.pipeline_run_id == newest_run and r.quantile not in quantiles:
                quantiles[r.quantile] = list(r.values)
        return ForecastSet(
            target=target,
            day=day,
            quantiles=quantiles,
            model_name=model_name,
            model_version=model_version,
        )

    async def save_forecast_metrics(self, pipeline_run_id: int | None, m: ForecastMetrics) -> None:
        self.session.add(
            ForecastMetric(
                pipeline_run_id=pipeline_run_id,
                target=m.target.value,
                model_name=m.model_name,
                mape_pct=m.mape_pct,
                mae=m.mae,
                pinball_p10=m.pinball_p10,
                pinball_p90=m.pinball_p90,
                n_folds=m.n_folds,
                detail=m.detail,
            )
        )
        await self.session.flush()

    # ------------------------------------------------------------- MILP runs
    async def create_milp_run(
        self,
        pipeline_run_id: int | None,
        day: date,
        stats: SolverStats,
        source: ScheduleSource = ScheduleSource.MILP,
    ) -> int:
        run = MilpRun(
            pipeline_run_id=pipeline_run_id,
            day=day,
            source=source.value,
            solver=stats.solver,
            status=stats.status,
            objective_inr=stats.objective_inr,
            gap=stats.gap,
            wall_time_s=stats.wall_time_s,
            n_binaries=stats.n_binaries,
        )
        self.session.add(run)
        await self.session.flush()
        return run.id

    async def save_schedule(self, milp_run_id: int, schedule: DispatchSchedule) -> None:
        for b in schedule.blocks:
            self.session.add(
                ScheduleBlockRow(
                    milp_run_id=milp_run_id,
                    block=b.block,
                    hydro_gen_mw=b.hydro_gen_mw,
                    psp_gen_mw=b.psp_gen_mw,
                    psp_pump_mw=b.psp_pump_mw,
                    market_buy_mw=b.market_buy_mw,
                    market_sell_mw=b.market_sell_mw,
                    ppa_drawal_mw=b.ppa_drawal_mw,
                    soc_mwh=b.soc_mwh,
                    spill_mwh=b.spill_mwh,
                    deviation_mw=b.deviation_mw,
                )
            )
        await self.session.flush()

    async def save_envelope(self, milp_run_id: int, envelope: Envelope) -> None:
        for b in envelope.blocks:
            self.session.add(
                EnvelopeRow(
                    milp_run_id=milp_run_id,
                    block=b.block,
                    psp_net_min_mw=b.psp_net_min_mw,
                    psp_net_max_mw=b.psp_net_max_mw,
                    market_net_min_mw=b.market_net_min_mw,
                    market_net_max_mw=b.market_net_max_mw,
                    soc_min_mwh=b.soc_min_mwh,
                    soc_max_mwh=b.soc_max_mwh,
                )
            )
        await self.session.flush()

    async def _latest_milp_run(self, day: date, source: ScheduleSource | None = None) -> MilpRun | None:
        stmt = select(MilpRun).where(MilpRun.day == day).order_by(MilpRun.id.desc())
        if source is not None:
            stmt = stmt.where(MilpRun.source == source.value)
        return (await self.session.execute(stmt)).scalars().first()

    async def latest_schedule(
        self, day: date, source: ScheduleSource | None = None
    ) -> DispatchSchedule | None:
        run = await self._latest_milp_run(day, source)
        if run is None:
            return None
        stmt = (
            select(ScheduleBlockRow)
            .where(ScheduleBlockRow.milp_run_id == run.id)
            .order_by(ScheduleBlockRow.block)
        )
        rows = (await self.session.execute(stmt)).scalars().all()
        blocks = [
            DispatchBlock(
                block=r.block,
                hydro_gen_mw=r.hydro_gen_mw,
                psp_gen_mw=r.psp_gen_mw,
                psp_pump_mw=r.psp_pump_mw,
                market_buy_mw=r.market_buy_mw,
                market_sell_mw=r.market_sell_mw,
                ppa_drawal_mw=r.ppa_drawal_mw,
                soc_mwh=r.soc_mwh,
                spill_mwh=r.spill_mwh,
                deviation_mw=r.deviation_mw,
            )
            for r in rows
        ]
        stats = SolverStats(
            solver=run.solver,
            status=run.status,
            objective_inr=run.objective_inr,
            gap=run.gap,
            wall_time_s=run.wall_time_s,
            n_binaries=run.n_binaries,
        )
        return DispatchSchedule(
            day=day,
            source=ScheduleSource(run.source),
            blocks=blocks,
            objective_cost_inr=run.objective_inr,
            solver=stats,
        )

    async def latest_envelope(self, day: date) -> Envelope | None:
        run = await self._latest_milp_run(day)
        if run is None:
            return None
        stmt = select(EnvelopeRow).where(EnvelopeRow.milp_run_id == run.id).order_by(EnvelopeRow.block)
        rows = (await self.session.execute(stmt)).scalars().all()
        if not rows:
            return None
        return Envelope(
            day=day,
            blocks=[
                EnvelopeBlock(
                    block=r.block,
                    psp_net_min_mw=r.psp_net_min_mw,
                    psp_net_max_mw=r.psp_net_max_mw,
                    market_net_min_mw=r.market_net_min_mw,
                    market_net_max_mw=r.market_net_max_mw,
                    soc_min_mwh=r.soc_min_mwh,
                    soc_max_mwh=r.soc_max_mwh,
                )
                for r in rows
            ],
        )

    # ------------------------------------------------------------- validation
    async def save_validation(self, pipeline_run_id: int | None, report: ValidationReport) -> int:
        row = TwinValidation(
            pipeline_run_id=pipeline_run_id,
            day=report.day,
            schedule_source=report.schedule_source.value,
            passed=report.passed,
            gates=[g.model_dump() for g in report.gates],
            scenarios=[s.model_dump() for s in report.scenarios],
        )
        self.session.add(row)
        await self.session.flush()
        k = report.kpis
        self.session.add(
            TwinKpi(
                validation_id=row.id,
                total_cost_inr=k.total_cost_inr,
                dsm_penalty_inr=k.dsm_penalty_inr,
                energy_served_mwh=k.energy_served_mwh,
                spill_mwh=k.spill_mwh,
                terminal_soc_mwh=k.terminal_soc_mwh,
                baseline_cost_inr=k.baseline_cost_inr,
                savings_vs_baseline_pct=k.savings_vs_baseline_pct,
                regret_vs_perfect_pct=k.regret_vs_perfect_pct,
            )
        )
        await self.session.flush()
        return row.id

    async def latest_validation(self, day: date) -> ValidationReport | None:
        stmt = select(TwinValidation).where(TwinValidation.day == day).order_by(TwinValidation.id.desc())
        row = (await self.session.execute(stmt)).scalars().first()
        if row is None:
            return None
        kpi_stmt = select(TwinKpi).where(TwinKpi.validation_id == row.id)
        kpi = (await self.session.execute(kpi_stmt)).scalars().first()
        if kpi is None:
            # W3: a validation row whose KPI row is missing is a data-integrity fault,
            # not a zero-cost day. Fail loudly instead of fabricating zeroed KPIs (which
            # would silently report total_cost_inr=0.0 and poison every downstream report).
            # The daily pipeline's degrade-not-raise wrapper turns this into manual mode.
            raise ValueError(f"validation {row.id} for {day} has no KPI row — data integrity error")
        kpis = TwinKPIs(
            total_cost_inr=kpi.total_cost_inr,
            dsm_penalty_inr=kpi.dsm_penalty_inr,
            energy_served_mwh=kpi.energy_served_mwh,
            spill_mwh=kpi.spill_mwh,
            terminal_soc_mwh=kpi.terminal_soc_mwh,
            baseline_cost_inr=kpi.baseline_cost_inr,
            savings_vs_baseline_pct=kpi.savings_vs_baseline_pct,
            regret_vs_perfect_pct=kpi.regret_vs_perfect_pct,
        )
        return ValidationReport(
            day=row.day,
            schedule_source=ScheduleSource(row.schedule_source),
            gates=[GateResult.model_validate(g) for g in row.gates],
            kpis=kpis,
            scenarios=[ScenarioResult.model_validate(s) for s in row.scenarios],
        )
