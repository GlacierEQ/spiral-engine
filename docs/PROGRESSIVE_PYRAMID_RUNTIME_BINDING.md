# Progressive Pyramid — live Spiral mission completion binding

Canonical Skill remains `GlacierEQ/mega-skills`; its version and SHA-256
are pinned in `config/progressive_pyramid_source_lock.json`. The local
`src/progressive_pyramid_source.py` adapter checks exact revision, source
bytes and contract schema, then invokes the verified canonical validator.
This adapter is not a second source of mission doctrine.

`SpiralEngine.run_mission` now accepts optional:
- `pyramid_state`: callable returning the latest original mission snapshot;
- `pyramid_verify`: independent provider-aware verifier for each criterion;
- `pyramid_source_dir`: exact location of installed canonical Skill.

All three are required for a Pyramid-bound execution, alongside the
existing independent `verify_outcome`. When the host adopts the Pyramid,
the source must be LOADED and mission_id, original_outcome, schema ID must
match the pre-existing durable journal before mutation. The live
`pyramid_state` is reloaded at terminal verification, permitting V1–V4
to advance during route execution. Completion requires every one of:
1. Original independent typed provider outcome verification.
2. Center Point explicitly MISSION_COMPLETE, not analysis convergence.
3. Source-native outcome receipt linked to the journal outcome.
4. Canonical V1–V4 lineage validator and verified criterion coverage.

If any condition fails, the original MissionRunner returns RESUMABLE and
preserves its continuity journal. No existing legacy API is removed or
retroactively called Pyramid-certified. Unbound callers retain the
original provider-backed mission-completion boundary.

Behavioral tests cover source verification, incomplete center, self-
attestation rejection, correct provider outcome and live mission execution.
Installing a Skill in an agent home directory is not proof that its agent
loaded the Skill or passed cross-agent certification.
