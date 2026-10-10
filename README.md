# Spiral Engine — Adaptive Compound Revolution Controller 🌀

> **A deterministic feedback controller for compounding repository and system improvements without confusing motion with progress.**

The Spiral Engine accepts a measured state, an intervention chosen by an upstream
optimizer, and the measured state after execution. It decides whether to
**CONTINUE, REVISE, PROMOTE, COMPLETE, or CONSTRAIN** the next revolution.

The engine is intentionally **domain- and language-blind**. The Tower of Babel can
decide that memory belongs with Odin, logic with Rust, or action with TypeScript;
Spiral decides whether the resulting intervention actually improved the system
without creating a larger downstream loss.

## Core loop

```text
measured state before
        ↓
upstream intervention
        ↓
execute real mutation
        ↓
measured state after
        ↓
evaluate:
  immediate gain
  mid-term gain
  far-term gain
  capability
  stability
  risk
  effort
  reversibility
  complexity
  critical regressions
        ↓
CONTINUE / REVISE / PROMOTE / COMPLETE / CONSTRAIN
        ↓
SHA-256 chained revolution receipt
        ↺
```

## Stable owner + frontier specialist

A specialization engine can preserve a stable production owner while proving a
stronger frontier specialist. Spiral promotes that frontier only when the
promotion evidence says it is:

- executable;
- behaviorally equivalent or better;
- behind an explicit interface;
- rollback-ready;
- measurably better;
- worth more than its interface cost;
- free of critical regressions.

This allows capability to expand without sacrificing stability.

## 9+ completion

The default controller target is:

- overall quality >= **9.0**;
- critical quality floor >= **8.5**.

A local score gain cannot hide a regression larger than the configured tolerance
on a critical dimension. Repeated non-progress becomes **CONSTRAINED** rather
than infinite-loop theater.

## Components

| Component | Purpose |
|---|---|
| `src/spiral_kernel.rs` | Minimal Rust pass-index execution kernel |
| `src/revolution_controller.py` | Adaptive multi-horizon revolution controller |
| `src/feedback_loop.py` | Small pure before/after signal helper |
| `src/promotion_authority.py` | Bound, short-lived promotion authority |
| `src/spiral_engine.py` | Backward-compatible facade + v2 controller exposure |
| `tests/test_revolution_controller.py` | Regression, promotion, completion, stagnation, receipt-chain tests |

## Python use

```python
from src import Impact, Intervention, QualityState, SpiralController

controller = SpiralController()

before = QualityState(
    overall=8.1,
    critical_floor=7.9,
    dimensions={"correctness": 8.3, "testing": 8.0, "security": 7.9},
    fingerprint="before",
)
after = QualityState(
    overall=8.7,
    critical_floor=8.4,
    dimensions={"correctness": 8.9, "testing": 8.6, "security": 8.4},
    fingerprint="after",
)

work = Intervention(
    intervention_id="logic:rust",
    title="focus Rust ownership of the safety-critical logic boundary",
    impact=Impact(
        near_term=.6,
        mid_term=.7,
        far_term=.8,
        capability_gain=.8,
        stability_gain=.9,
        reversibility=.9,
        risk=.2,
        effort=.3,
        complexity_delta=.1,
    ),
)

receipt = controller.record(before, after, work)
print(receipt.signal)
```

## Mission-grounded improvement: know what better means

The Operator's full intended outcome is the definition of success. Quality
scores alone are feedback and may **never** redefine a mission's goal.

The additive `ImprovementContract` and `evaluate_improvement` system can
bind outcome/capability/integrity criteria to a mission, detect lost prior
capabilities and verified facts, and require independent evidence for gains.
`SpiralEngine.run_mission` accepts optional instrumented observations and
saves assessment receipts into the existing `ContinuityJournal`. Legacy
calls retain existing behavior and cannot claim a verified improvement merely
because a local quality score crossed its configured threshold.

See [Mission-Bound Improvement Contract](docs/MISSION_BOUND_IMPROVEMENT.md)
for inheritance, provider proof, counter-mold regression tests and remaining
host-runtime integration work.

## Verification

```bash
python -m compileall -q src tests
python -m unittest discover -s tests -p 'test_*.py' -v
```

GitHub Actions runs the same suite and emits a chained revolution artifact.


## Original engine + integrated mission continuity

The original measured feedback controller, quality policy, promotion authority,
Rust kernel, and legacy `SpiralEngine` facade are **preserved**. These now work
with a durable mission execution layer; this extends the existing product.

| Existing behavior (preserved) | Added capability |
|---|---|
| Measure before/after quality and downstream effect | Retain each revolution across sessions |
| `CONTINUE`, `REVISE`, `PROMOTE`, `COMPLETE`, `CONSTRAINED` feedback | Separate quality-level `COMPLETE` from mission-outcome completion |
| Promotion and regression decisions | Terminal outcome requires matching type and independent provider verification |
| SHA-256-chained revolution receipts | Append-only mission history with optional independent HMAC authentication |
| Existing facade APIs and intervention execution | `SpiralEngine.run_mission()` joins routes, feedback and durable resumption |
| Testable intervention executor | Record attempts before external work; reconcile uncertainty instead of replaying |

### Operational contract

1. Open a `ContinuityJournal` for the exact assigned mission and terminal human outcome.
2. Supply an independently protected `integrity_key` to authenticate history. Without a separate key, a SHA-256 chain detects accidental corruption but does not prevent deliberate rewriting. Store the key outside Git and logs and retain it across sessions.
3. Supply real provider adapters to measure quality, propose the original `Intervention`, execute an action, retrieve outcome evidence, and independently verify that outcome. A textual receipt reference is not automatically proof.
4. Call `SpiralEngine.run_mission(journal, routes=..., evaluate=..., propose=..., execute=..., outcome_evidence=..., verify_outcome=...)`.
5. The original quality controller emits its unaltered feedback receipts. The journal preserves them along with facts, corrections, hierarchical tasks and continuation cursor. Reaching quality 9+ does not finish an employment, court or deployment mission.
6. Resume with the same mission ID, objective, outcome and integrity key. The controller restores its previous measured revolution chain. A route interrupted after an external side effect must be reconciled with the provider before a new intentional attempt; the same route is not blindly replayed.
7. Deployment and observation of the assigned external outcome remain explicit goals; a passing test, generated document or merged PR is not equivalent to that outcome.

The action callback `execute(route, intervention)` must return `RouteResult`.
The `verify_outcome(OutcomeEvidence) -> bool` callback is required before
final mission completion. Implement it using authoritative provider readback,
never an unconditional `True` or fabricated receipt. Source-backed facts
should be inherited until genuinely superseded by newer authoritative evidence.

### Full regression checks

```bash
python -m compileall -q src tests
python -m unittest discover -s tests -p 'test_*.py' -v
```

GitHub Actions executes this suite and publishes a revolution proof artifact.
Tests demonstrate program behavior, not an external employer, court, or deployment result.
