"""Mission-bound improvement semantics for the Spiral Engine.

A reported quality score is a measurement, not an improvement. The Operator's
mission contract fixes the objective; before/after observations preserve
existing capability and verified fact identities. Positive changes must pass
an independent evidence callback. This layer does not assert terminal mission
completion: ContinuityJournal.complete owns that stronger proof boundary.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from hashlib import sha256
from json import dumps
from math import isfinite
from typing import Any, Callable, Mapping


KINDS = frozenset({
    "outcome", "capability", "integrity", "execution",
    "memory", "reliability", "leverage", "verification",
})
STATES = frozenset({"IMPROVED", "REGRESSION", "UNVERIFIED", "NO_GAIN"})


def _digest(data: Any) -> str:
    return sha256(dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()


def _nonblank(value: str, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value


def _unique(items: tuple[str, ...], name: str) -> None:
    if any(not isinstance(item, str) or not item.strip() for item in items):
        raise ValueError(f"{name} contains an empty or invalid identifier")
    if len(items) != len(set(items)):
        raise ValueError(f"{name} must have unique identifiers")


@dataclass(frozen=True)
class ImprovementCriterion:
    key: str
    kind: str

    def __post_init__(self) -> None:
        _nonblank(self.key, "criterion key")
        if self.kind not in KINDS:
            raise ValueError(f"unknown improvement kind: {self.kind}")


@dataclass(frozen=True)
class ImprovementContract:
    mission_id: str
    objective: str
    terminal_outcome: str
    criteria: tuple[ImprovementCriterion, ...]
    protected_capabilities: tuple[str, ...] = ()
    source_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for key in ("mission_id", "objective", "terminal_outcome"):
            _nonblank(getattr(self, key), key)
        if not self.criteria or not all(isinstance(c, ImprovementCriterion) for c in self.criteria):
            raise ValueError("typed improvement criteria required")
        keys = tuple(c.key for c in self.criteria)
        _unique(keys, "criteria")
        if not any(c.kind == "outcome" for c in self.criteria):
            raise ValueError("contract requires at least one outcome criterion")
        _unique(self.protected_capabilities, "protected capabilities")
        _unique(self.source_refs, "source references")

    @property
    def fingerprint(self) -> str:
        return _digest(asdict(self))


@dataclass(frozen=True)
class ImprovementObservation:
    measures: Mapping[str, float]
    capabilities: tuple[str, ...] = ()
    verified_facts: tuple[str, ...] = ()
    evidence: Mapping[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.measures, Mapping):
            raise ValueError("measures must be a mapping")
        for name, value in self.measures.items():
            _nonblank(name, "measure name")
            if (not isinstance(value, (float, int)) or isinstance(value, bool)
                    or not isfinite(value) or not 0 <= value <= 10):
                raise ValueError(f"invalid bounded measure: {name}")
        _unique(self.capabilities, "capabilities")
        _unique(self.verified_facts, "verified facts")
        if not isinstance(self.evidence, Mapping):
            raise ValueError("evidence must be a mapping")
        for name, ref in self.evidence.items():
            _nonblank(name, "evidence key")
            if not isinstance(ref, str):
                raise ValueError("evidence references must be strings")

    def snapshot(self) -> dict[str, Any]:
        return {
            "measures": {key: float(value) for key, value in sorted(self.measures.items())},
            "capabilities": sorted(self.capabilities),
            "verified_facts": sorted(self.verified_facts),
            "evidence": dict(sorted(self.evidence.items())),
        }


@dataclass(frozen=True)
class ImprovementAssessment:
    mission_id: str
    objective: str
    terminal_outcome: str
    state: str
    improvements: tuple[str, ...]
    regressions: tuple[str, ...]
    lost_capabilities: tuple[str, ...]
    lost_facts: tuple[str, ...]
    unverified: tuple[str, ...]
    measure_deltas: Mapping[str, float]
    evidence: Mapping[str, str]
    contract_sha256: str
    before_sha256: str
    after_sha256: str
    digest: str

    def verify(self) -> bool:
        body = asdict(self)
        supplied = body.pop("digest")
        return self.state in STATES and supplied == _digest(body)


EvidenceVerifier = Callable[[str, str, float, float], bool]


def evaluate_improvement(
    contract: ImprovementContract,
    before: ImprovementObservation,
    after: ImprovementObservation,
    *,
    verify_evidence: EvidenceVerifier | None = None,
) -> ImprovementAssessment:
    """Evaluate *observed, mission-relevant* improvement without redefining the mission.

    Any lost prior capability or verified fact, or any regressed criterion, is
    an explicit regression. Gains require independent source verification, not
    merely supplied receipt strings. A nonterminal improvement cannot complete
    the human outcome or supersede its required provider receipt.
    """
    if not isinstance(contract, ImprovementContract):
        raise TypeError("an Operator-bound ImprovementContract is required")
    if not isinstance(before, ImprovementObservation) or not isinstance(after, ImprovementObservation):
        raise TypeError("typed before and after observations required")

    required = {c.key for c in contract.criteria}
    if set(before.measures) != required or set(after.measures) != required:
        raise ValueError("both observations must cover exactly the mission's improvement criteria")

    before_caps, after_caps = set(before.capabilities), set(after.capabilities)
    if not set(contract.protected_capabilities).issubset(before_caps):
        raise ValueError("protected baseline capabilities must exist in the before observation")
    lost_capabilities = tuple(sorted(before_caps - after_caps))
    lost_facts = tuple(sorted(set(before.verified_facts) - set(after.verified_facts)))

    measure_deltas = {
        key: round(float(after.measures[key]) - float(before.measures[key]), 6)
        for key in sorted(required)
    }
    regressions = tuple(key for key, delta in measure_deltas.items() if delta < 0)
    gains = [key for key, delta in measure_deltas.items() if delta > 0]
    additions = [f"capability:{key}" for key in sorted(after_caps - before_caps)]
    improvements = tuple(gains + additions)

    unverified = []
    evidence: dict[str, str] = {}
    for key in improvements:
        ref = after.evidence.get(key, "")
        old, new = (
            (0.0, 1.0) if key.startswith("capability:")
            else (float(before.measures[key]), float(after.measures[key]))
        )
        if isinstance(ref, str) and ref.strip():
            evidence[key] = ref
        if not isinstance(ref, str) or not ref.strip() or verify_evidence is None:
            unverified.append(key)
            continue
        try:
            verified = verify_evidence(key, ref, old, new) is True
        except Exception:
            verified = False
        if not verified:
            unverified.append(key)

    if regressions or lost_capabilities or lost_facts:
        state = "REGRESSION"
    elif unverified:
        state = "UNVERIFIED"
    elif improvements:
        state = "IMPROVED"
    else:
        state = "NO_GAIN"

    body = {
        "mission_id": contract.mission_id,
        "objective": contract.objective,
        "terminal_outcome": contract.terminal_outcome,
        "state": state,
        "improvements": improvements,
        "regressions": regressions,
        "lost_capabilities": lost_capabilities,
        "lost_facts": lost_facts,
        "unverified": tuple(unverified),
        "measure_deltas": measure_deltas,
        "evidence": evidence,
        "contract_sha256": contract.fingerprint,
        "before_sha256": _digest(before.snapshot()),
        "after_sha256": _digest(after.snapshot()),
    }
    return ImprovementAssessment(**body, digest=_digest(body))
