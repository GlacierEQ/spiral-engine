# Mission-bound improvement contract

## Why the Spiral must know what `better` means

The Spiral Engine's existing quality controller measures before/after scores and
produces `CONTINUE`, `REVISE`, `PROMOTE`, `COMPLETE`, or `CONSTRAINED`.
Those are **local quality-feedback signals**, not a decision that the Operator's
human objective has been met. The existing mission continuity layer independently
requires the specified terminal outcome and provider proof.

**Improvement is neither motion nor numerical score gain.** It must be grounded
in the Operator's assigned objective and accompanied by source-verifiable gains
that preserve previous capability and verified evidence.

The contract is **additive**: it preserves the quality controller, journal,
provider outcome checks, historical receipts, original mission identity, and
legacy API. It cannot redefine or silently shorten a mission.

## Contract and invariants

- `ImprovementContract` binds the unchanged `mission_id`, original `objective`,
  actual `terminal_outcome`, typed success criteria, protected capabilities
  and optional source references (for the transcribed foundation).
- At least one criterion must measure **outcome progress**. Other criteria may
  represent capability, reliability, execution, memory, integrity, verification,
  and future leverage. The Operator and source-bearing mission contract supply
  these meanings; an evaluator does **not** get to choose an easier objective.
- `ImprovementObservation` reports before/after measurements (0–10 for each
  criterion), capability identifiers, verified-fact identifiers and source refs.
  These numbers are observations, not automatically proof or mission truth.
- `evaluate_improvement` first detects lost capabilities, missing previously
  verified facts, and deterioration in **any** bound criterion. These are
  `REGRESSION` regardless of a headline quality gain.
- Gains in criterion measures and newly claimed capabilities require source
  references and an **independent `verify_evidence` callback**. The callback
  must actually check current source/provider proof for that exact claimed
  delta. An arbitrary string, a summary, a generated receipt, or a verifier
  that always returns `True` does not establish real-world proof.
- States: `IMPROVED`, `REGRESSION`, `UNVERIFIED`, `NO_GAIN`. They are
  **assessments**, never substitutes for the typed terminal mission outcome.
- Assessments carry a deterministic SHA-256 digest and are appended to the
  existing durable mission journal, whose optional independent integrity key
  authenticates history. A self-hash alone is *not* independent attestation.
- In `SpiralEngine.run_mission`, improvement instrumentation is opt-in
  for backward compatibility, but partially configured instrumentation fails
  before mutation. The mission identity must match the existing journal.
  Journal-verified fact keys must be represented in each before/after
  improvement observation, preventing the assessor from quietly omitting
  verified memory as though it never existed.
- If an old caller does not bind an improvement contract, its local quality
  score must **not** be represented as verified mission improvement. The
  mission can still execute under the original outcome verification gate.
- A local blocker changes route and preserves the mission. Evaluation is
  ongoing; a numerical threshold alone cannot end a mission.

## Runtime integration

```python
from src import ImprovementContract, ImprovementCriterion, ImprovementObservation

contract = ImprovementContract(
    mission_id=journal.mission_id,
    objective=journal.objective,
    terminal_outcome=journal.terminal_outcome,
    criteria=(
        ImprovementCriterion("outcome_progress", "outcome"),
        ImprovementCriterion("runtime_reliability", "reliability"),
        ImprovementCriterion("memory_integrity", "memory"),
    ),
    protected_capabilities=("context-recovery", "git-readback"),
    source_refs=("operator:mission-brief",),
)

# observe() and verify() are project-owned, source-backed adapters:
# - observe() must include all journal verified-fact keys
# - verify(name, reference, old, new) checks actual provider-native proof
result = engine.run_mission(
    journal, routes=routes, evaluate=evaluate_quality,
    propose=propose, execute=execute, outcome_evidence=outcome_evidence,
    verify_outcome=verify_terminal_outcome,
    improvement_contract=contract,
    observe_improvement=observe,
    verify_improvement=verify,
)
```

For a newly installed coding-agent host such as OMP, compile the *same* Operator
contract into a native boot/instruction projection, and independently check
that the loaded runtime actually uses it. Merely creating or copying a Markdown
file is not sufficient. No OMP host deployment is implied by this repository
change.

## Adversarial acceptance cases

1. Quality reaches 9.5 but job placement remains unverified:
   improvement may be measured but **employment mission remains RESUMABLE**.
2. Score increases from 2 to 9.9 with a fabricated assistant receipt:
   `UNVERIFIED`.
3. Score rises while context recovery disappears: `REGRESSION`.
4. Score rises while a verified fact disappears: `REGRESSION`.
5. One criterion degrades while another improves: `REGRESSION`.
6. A new capability is merely claimed without independent proof:
   `UNVERIFIED`.
7. Nothing materially changes: `NO_GAIN`.
8. A rehydrated mission preserves assessment receipt digests and can continue.
9. An observation that omits authoritative journal fact keys fails before
   work can be counted as an improvement.
10. Legacy quality/mission behavior remains operational.

## Continuation frontier

The mission-specific score semantics still require a provider-native observation
and verification adapter per domain. The foundation transcription/counter-mold
pipeline should compile those definitions from versioned Operator evidence,
run the adversarial suite on each correction, and propagate the resulting
verified contract to OMP, APEX, and other hosts. Do not claim those host
adapters are deployed until runtime readback proves they are active.
