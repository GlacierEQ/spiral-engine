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

## Verification

```bash
python -m compileall -q src tests
python -m unittest discover -s tests -p 'test_*.py' -v
```

GitHub Actions runs the same suite and emits a chained revolution artifact.
