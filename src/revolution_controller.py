"""Generic compound-revolution controller.

Spiral deliberately does not decide which language, framework, or architecture a
repository should use. Upstream engines (for example the Tower of Babel) provide
an intervention. Spiral owns the adaptive control loop:

    state before -> intervention -> state after -> evaluate -> next signal

The controller optimizes for durable progress across immediate and downstream
impact while refusing to treat local score gain as success when a critical
quality axis regresses.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

SCHEMA = "glaciereq.spiral-revolution.v2"
SIGNALS = frozenset({"CONTINUE", "REVISE", "PROMOTE", "COMPLETE", "CONSTRAINED"})


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _bounded(value: float, *, low: float = 0.0, high: float = 10.0) -> float:
    value = float(value)
    if not low <= value <= high:
        raise ValueError(f"value {value} outside [{low}, {high}]")
    return value


@dataclass(frozen=True)
class QualityState:
    overall: float
    critical_floor: float
    dimensions: Mapping[str, float]
    fingerprint: str = ""

    def __post_init__(self) -> None:
        _bounded(self.overall)
        _bounded(self.critical_floor)
        for name, score in self.dimensions.items():
            if not isinstance(name, str) or not name:
                raise ValueError("dimension names must be non-empty strings")
            _bounded(score)

    def normalized(self) -> dict[str, Any]:
        return {
            "overall": round(float(self.overall), 6),
            "critical_floor": round(float(self.critical_floor), 6),
            "dimensions": {
                key: round(float(value), 6)
                for key, value in sorted(self.dimensions.items())
            },
            "fingerprint": self.fingerprint,
        }


@dataclass(frozen=True)
class Impact:
    near_term: float
    mid_term: float
    far_term: float
    capability_gain: float
    stability_gain: float
    reversibility: float
    risk: float
    effort: float
    complexity_delta: float

    def __post_init__(self) -> None:
        for value in (
            self.near_term, self.mid_term, self.far_term, self.capability_gain,
            self.stability_gain, self.reversibility, self.risk, self.effort,
        ):
            _bounded(value, high=1.0)
        if not -1.0 <= float(self.complexity_delta) <= 1.0:
            raise ValueError("complexity_delta must be within [-1, 1]")

    @property
    def net(self) -> float:
        benefit = (
            .20 * self.near_term
            + .24 * self.mid_term
            + .30 * self.far_term
            + .22 * self.capability_gain
            + .26 * self.stability_gain
            + .08 * self.reversibility
        )
        cost = (
            .25 * self.risk
            + .16 * self.effort
            + .22 * max(0.0, self.complexity_delta)
        )
        return round(benefit - cost, 6)


@dataclass(frozen=True)
class Intervention:
    intervention_id: str
    title: str
    impact: Impact
    role: str | None = None
    candidate: str | None = None
    completion_signal: str = ""

    def __post_init__(self) -> None:
        if not self.intervention_id.strip():
            raise ValueError("intervention_id required")
        if not self.title.strip():
            raise ValueError("title required")


@dataclass(frozen=True)
class PromotionEvidence:
    required: bool = False
    execution_ready: bool = False
    behavioral_parity: bool = False
    rollback_ready: bool = False
    explicit_interface: bool = False
    benchmark_gain: float = 0.0
    interface_cost: float = 0.0

    def __post_init__(self) -> None:
        for value in (self.benchmark_gain, self.interface_cost):
            if not -1.0 <= float(value) <= 1.0:
                raise ValueError("promotion gain/cost must be within [-1, 1]")

    @property
    def ready(self) -> bool:
        if not self.required:
            return False
        return (
            self.execution_ready
            and self.behavioral_parity
            and self.rollback_ready
            and self.explicit_interface
            and self.benchmark_gain > self.interface_cost
            and self.benchmark_gain > 0.0
        )


@dataclass(frozen=True)
class SpiralPolicy:
    target: float = 9.0
    critical_floor: float = 8.5
    regression_tolerance: float = 0.5
    min_progress: float = 0.01
    stagnation_limit: int = 2

    def __post_init__(self) -> None:
        _bounded(self.target)
        _bounded(self.critical_floor)
        if not 0.0 <= self.regression_tolerance <= 10.0:
            raise ValueError("regression_tolerance")
        if self.min_progress < 0.0:
            raise ValueError("min_progress")
        if self.stagnation_limit < 1:
            raise ValueError("stagnation_limit")


@dataclass(frozen=True)
class RevolutionReceipt:
    schema: str
    revolution: int
    signal: str
    intervention_id: str
    before: Mapping[str, Any]
    after: Mapping[str, Any]
    impact_net: float
    score_delta: float
    critical_regressions: tuple[str, ...]
    improvements: tuple[str, ...]
    promotion_ready: bool
    reason: str
    previous_receipt_sha256: str
    receipt_sha256: str

    def verify(self) -> bool:
        payload = asdict(self)
        supplied = payload.pop("receipt_sha256")
        return supplied == _sha256(payload)


StateEvaluator = Callable[[], QualityState]
InterventionProposer = Callable[[QualityState], Intervention | None]
InterventionExecutor = Callable[[Intervention], bool]
PromotionEvaluator = Callable[[Intervention, QualityState, QualityState], PromotionEvidence]


def _dimension_changes(
    before: QualityState,
    after: QualityState,
    tolerance: float,
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    regressions: list[str] = []
    improvements: list[str] = []
    keys = sorted(set(before.dimensions) | set(after.dimensions))
    for key in keys:
        old = float(before.dimensions.get(key, 0.0))
        new = float(after.dimensions.get(key, 0.0))
        if new < old - tolerance:
            regressions.append(key)
        elif new > old + 1e-9:
            improvements.append(key)
    return tuple(regressions), tuple(improvements)


def decide_revolution(
    *,
    revolution: int,
    before: QualityState,
    after: QualityState,
    intervention: Intervention,
    policy: SpiralPolicy = SpiralPolicy(),
    promotion: PromotionEvidence | None = None,
    consecutive_stagnation: int = 0,
    previous_receipt_sha256: str = "",
) -> RevolutionReceipt:
    if revolution < 1:
        raise ValueError("revolution must be >= 1")
    promotion = promotion or PromotionEvidence()
    regressions, improvements = _dimension_changes(
        before, after, policy.regression_tolerance
    )
    score_delta = round(after.overall - before.overall, 6)
    same_fingerprint = bool(
        before.fingerprint
        and after.fingerprint
        and before.fingerprint == after.fingerprint
    )
    stagnant = same_fingerprint or score_delta < policy.min_progress

    if regressions:
        signal = "REVISE"
        reason = "critical quality regression detected: " + ", ".join(regressions)
    elif after.overall >= policy.target and after.critical_floor >= policy.critical_floor:
        signal = "COMPLETE"
        reason = (
            f"balanced target reached: overall={after.overall:.3f}, "
            f"critical_floor={after.critical_floor:.3f}"
        )
    elif promotion.ready:
        signal = "PROMOTE"
        reason = (
            "frontier promotion evidence satisfied: executable, parity-tested, "
            "rollback-ready, explicit interface, realized gain exceeds interface cost"
        )
    elif stagnant and consecutive_stagnation + 1 >= policy.stagnation_limit:
        signal = "CONSTRAINED"
        reason = "progress stagnated across the configured revolution limit"
    elif stagnant:
        signal = "REVISE"
        reason = "intervention did not produce enough measurable progress"
    else:
        signal = "CONTINUE"
        reason = (
            f"measured progress +{score_delta:.3f}; continue compounding while "
            "re-evaluating downstream impact"
        )

    body = {
        "schema": SCHEMA,
        "revolution": revolution,
        "signal": signal,
        "intervention_id": intervention.intervention_id,
        "before": before.normalized(),
        "after": after.normalized(),
        "impact_net": intervention.impact.net,
        "score_delta": score_delta,
        "critical_regressions": regressions,
        "improvements": improvements,
        "promotion_ready": promotion.ready,
        "reason": reason,
        "previous_receipt_sha256": previous_receipt_sha256,
    }
    return RevolutionReceipt(
        **body,
        receipt_sha256=_sha256(body),
    )


class SpiralController:
    """Stateful receipt chain around the pure revolution decision function."""

    def __init__(self, policy: SpiralPolicy | None = None) -> None:
        self.policy = policy or SpiralPolicy()
        self._receipts: list[RevolutionReceipt] = []
        self._stagnation = 0

    @property
    def receipts(self) -> tuple[RevolutionReceipt, ...]:
        return tuple(self._receipts)

    @property
    def previous_receipt_sha256(self) -> str:
        return self._receipts[-1].receipt_sha256 if self._receipts else ""

    def record(
        self,
        before: QualityState,
        after: QualityState,
        intervention: Intervention,
        promotion: PromotionEvidence | None = None,
    ) -> RevolutionReceipt:
        delta = after.overall - before.overall
        same = bool(
            before.fingerprint
            and after.fingerprint
            and before.fingerprint == after.fingerprint
        )
        stagnant_now = same or delta < self.policy.min_progress

        receipt = decide_revolution(
            revolution=len(self._receipts) + 1,
            before=before,
            after=after,
            intervention=intervention,
            policy=self.policy,
            promotion=promotion,
            consecutive_stagnation=self._stagnation,
            previous_receipt_sha256=self.previous_receipt_sha256,
        )
        self._receipts.append(receipt)

        if receipt.signal in {"CONTINUE", "PROMOTE", "COMPLETE"}:
            self._stagnation = 0
        elif stagnant_now:
            self._stagnation += 1
        else:
            self._stagnation = 0
        return receipt

    def run(
        self,
        *,
        evaluate: StateEvaluator,
        propose: InterventionProposer,
        execute: InterventionExecutor,
        promotion_evidence: PromotionEvaluator | None = None,
        max_revolutions: int = 12,
    ) -> tuple[RevolutionReceipt, ...]:
        if max_revolutions < 1:
            raise ValueError("max_revolutions")

        state = evaluate()
        for _ in range(max_revolutions):
            if (
                state.overall >= self.policy.target
                and state.critical_floor >= self.policy.critical_floor
            ):
                break

            intervention = propose(state)
            if intervention is None:
                break
            if not execute(intervention):
                # Executor refusal is an external constraint; preserve the current
                # state and produce a deterministic constrained receipt.
                synthetic = QualityState(
                    overall=state.overall,
                    critical_floor=state.critical_floor,
                    dimensions=state.dimensions,
                    fingerprint=state.fingerprint,
                )
                receipt = self.record(state, synthetic, intervention)
                if receipt.signal != "CONSTRAINED":
                    body = asdict(receipt)
                    body.pop("receipt_sha256")
                    body["signal"] = "CONSTRAINED"
                    body["reason"] = "intervention executor declined or could not mutate state"
                    replacement = RevolutionReceipt(
                        **body,
                        receipt_sha256=_sha256(body),
                    )
                    self._receipts[-1] = replacement
                break

            after = evaluate()
            promotion = (
                promotion_evidence(intervention, state, after)
                if promotion_evidence is not None
                else None
            )
            receipt = self.record(state, after, intervention, promotion)
            state = after
            if receipt.signal in {"COMPLETE", "CONSTRAINED"}:
                break
            if receipt.signal == "REVISE" and self._stagnation >= self.policy.stagnation_limit:
                break

        return self.receipts

    def export(self) -> dict[str, Any]:
        receipts = [asdict(receipt) for receipt in self._receipts]
        return {
            "schema": "glaciereq.spiral-history.v2",
            "policy": asdict(self.policy),
            "revolution_count": len(receipts),
            "head_receipt_sha256": self.previous_receipt_sha256,
            "receipts": receipts,
        }

    def write(self, path: Path | str) -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            json.dumps(self.export(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )


def verify_receipt_chain(receipts: Sequence[RevolutionReceipt]) -> tuple[bool, str | None]:
    previous = ""
    for index, receipt in enumerate(receipts, 1):
        if receipt.revolution != index:
            return False, f"REVOLUTION_SEQUENCE:{index}"
        if receipt.signal not in SIGNALS:
            return False, f"INVALID_SIGNAL:{receipt.signal}"
        if receipt.previous_receipt_sha256 != previous:
            return False, f"CHAIN_BREAK:{index}"
        if not receipt.verify():
            return False, f"BAD_RECEIPT_HASH:{index}"
        previous = receipt.receipt_sha256
    return True, None
