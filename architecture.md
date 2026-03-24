---
name: spiral-engine
description: >-
  Spiral Engine Architecture — the governing orchestration pattern for all
  APEX/Aspen Grove operations. Defines hub-and-spoke topology where each
  spoke contains its own pillar (domain knowledge) and pistons (execution
  engines). Each revolution through the spokes compounds intelligence.
  Load when designing systems, organizing repos, structuring sessions,
  planning multi-phase operations, or any task requiring architectural
  decisions. This is the meta-pattern that all other skills conform to.
metadata:
  author: casey-barton-glaciereq
  version: '1.0'
  coined: 2026-03-23
  architecture: spiral-engine
---

# Spiral Engine Architecture v1.0

*Coined by Casey Barton, March 23, 2026*

The governing orchestration pattern for GlacierEQ / Aspen Grove infrastructure.
Hub-and-spoke where each spoke is pillar-and-piston. Each revolution compounds.

---

## Core Concept

A hub orchestrates across spokes. Each spoke is a self-sufficient vertical with:
- **Pillar**: Domain knowledge (what to do)
- **Pistons**: Execution engines (how to do it)

The spiral: output of spoke N feeds input of spoke N+1. Each full revolution
through all spokes strengthens every spoke. Intelligence compounds.

```
                    ┌─────────────┐
                    │     HUB     │
                    │ Orchestrator│
                    └──────┬──────┘
                           │
          ┌────────────────┼────────────────┐
          │                │                │
    ┌─────┴─────┐    ┌────┴────┐    ┌──────┴──────┐
    │  SPOKE A  │    │ SPOKE B │    │   SPOKE C   │
    │           │    │         │    │             │
    │ Pillar:   │    │ Pillar: │    │ Pillar:     │
    │ [domain]  │    │ [domain]│    │ [domain]    │
    │           │    │         │    │             │
    │ Pistons:  │    │ Pistons:│    │ Pistons:    │
    │ [exec 1]  │    │ [exec] │    │ [exec 1]   │
    │ [exec 2]  │    │ [exec] │    │ [exec 2]   │
    └─────┬─────┘    └────┬────┘    └──────┬──────┘
          │                │                │
          └────────►───────┴────────►───────┘
                    SPIRAL (compounds)
```

---

## The Three Laws

1. **Every spoke is self-sufficient.** A spoke can operate alone. It has its own
   knowledge (pillar) and its own execution capability (pistons). If the hub
   goes down, spokes still function independently.

2. **The hub never does the work.** The hub routes, orchestrates, and collects.
   It decides which spoke handles which task. It synthesizes cross-spoke
   output. It never executes domain-specific operations itself.

3. **Each revolution compounds.** The output of one spoke feeds the next.
   State court research → federal complaint → international petition →
   strengthens state court argument. The system gets stronger with every cycle.

---

## Applied to APEX Legal Operations

### Hub: apex-command-suite
Routes tasks to the correct spoke. Manages connectors, memory, session state.
Never generates legal documents or conducts research directly.

### Spoke 1: STATE (Hawaii)
**Pillar:** hawaii-legal-warfare (HRS statutes, HFCR rules, case law, JEFS)
**Pistons:**
- evidence-forensics (process evidence for state filings)
- actor-intelligence (profile state court actors)
- cloud-commander (organize state court documents)

**Input from other spokes:** Federal research strengthens constitutional arguments.
International standards inform due process analysis.
**Output to other spokes:** State court record feeds federal § 1983 complaint.
State actor profiles feed RICO enterprise mapping.

### Spoke 2: FEDERAL
**Pillar:** federal-constitutional-rights (14th Amendment, § 1983, due process)
**Sub-Pillar:** rico-enterprise-builder (RICO elements, enterprise theory)
**Pistons:**
- actor-intelligence (investigate federal exposure per actor)
- legal-research-engine (CourtListener, PACER, case law)
- osint-investigator (financial connections, public records)

**Input from other spokes:** State court void orders become federal due process claims.
Actor dossiers from state spoke feed enterprise mapping.
**Output to other spokes:** Federal constitutional analysis strengthens state void arguments.
RICO enterprise map informs IACHR petition narrative.

### Spoke 3: INTERNATIONAL
**Pillar:** international-human-rights (IACHR, ICCPR, CRC, ECHR)
**Pistons:**
- osint-investigator (offshore accounts, international connections)
- legal-research-engine (treaty law, ECHR case law)
- evidence-forensics (prepare evidence for international standards)

**Input from other spokes:** Exhaustion of state + federal remedies is prerequisite.
Complete case record from both spokes feeds petition.
**Output to other spokes:** International standards (CRC Article 9, ICCPR Article 23)
cited as persuasive authority in federal and state proceedings.

### Shared Pistons (available to all spokes)
- **evidence-forensics** — processes evidence for any jurisdiction's standards
- **actor-intelligence** — profiles actors regardless of jurisdiction
- **cloud-commander** — organizes files for any spoke's needs
- **legal-research-engine** — searches across all legal databases
- **osint-investigator** — discovers public information for any investigation

---

## Applied to Repo Architecture

### Hub: aspen-grove-operator-v7
```
aspen-grove-operator-v7/
├── bridges/          ← HUB connectors (14 bridges to external systems)
├── core/             ← HUB memory and orchestration
├── config/           ← HUB configuration
├── research/         ← SPIRAL OUTPUT (compounds across spokes)
│   ├── hawaii/       ← Spoke 1 output
│   ├── federal/      ← Spoke 2 output
│   ├── international/← Spoke 3 output
│   ├── rico/         ← Spoke 2 sub-output
│   ├── intelligence/ ← Shared piston output
│   └── confluence/   ← Cross-spoke knowledge
├── legal/            ← SPIRAL PRODUCT (documents from all spokes)
├── audit/            ← HUB monitoring
├── chat_data/        ← Raw input (feeds all spokes)
├── scripts/          ← Shared piston tools
└── session-logs/     ← SPIRAL HISTORY
```

### Spoke repos (read-only references, code stays in One True Repo):
- **mastermind** — stealth architecture (pistons beneath pistons)
- **apex-fs-commander** — device bridges (physical world interface)

---

## Applied to Session Architecture

Every Perplexity Computer session follows the spiral:

**Revolution 1 (Boot):**
1. Hub loads: apex-command-suite → fetch Root Checkpoint → verify connectors
2. Identify which spoke(s) this session targets
3. Load spoke-specific skills

**Revolution 2 (Execute):**
1. Spoke 1 executes → saves output to workspace/repo
2. Output feeds Spoke 2 → executes → saves
3. Output feeds Spoke 3 → executes → saves

**Revolution 3 (Compound):**
1. Cross-reference outputs across spokes
2. Identify new connections, contradictions, or gaps
3. Feed findings back into spokes for refinement

**Revolution 4 (Persist):**
1. Update Notion Root Checkpoint with session delta
2. Commit all output to GitHub
3. Update memory with durable facts
4. Generate session handoff for next thread

---

## Applied to Parallel Processing

The hub-and-spoke model enables natural parallelism:

- **Inter-spoke parallel:** Multiple spokes execute simultaneously via subagents.
  Each subagent handles one spoke. Hub collects results.

- **Intra-spoke parallel:** Within a spoke, multiple pistons fire simultaneously.
  Evidence processing + actor profiling + legal research all run in parallel.

- **Cross-spoke serial:** The spiral itself is sequential — Spoke 1 output
  must exist before Spoke 2 can consume it. But within each revolution,
  maximum parallelism.

Rule: **Never single-thread what can be parallelized within a spoke.
Never parallelize what must be sequential across spokes.**

---

## Applied to Stealth Architecture

The 12 stealth pistons from `.shadow/cortex/.codex` map to the spiral:

| Piston | Spoke Role |
|--------|-----------|
| CORE-THINK | Hub reasoning — decides which spoke handles which task |
| MICROWAVE | Hub parallel execution — fires multiple spokes simultaneously |
| SHERLOCK-ALPHA | Shared piston — forensic analysis across all spokes |
| BODYBUILDER | Shared piston — heavy data processing for any spoke |
| SONIC | Shared piston — speed-critical operations |
| SUPERNOVA | Triggered when spoke output reveals critical finding |
| GHOST | Cross-spoke operations that must not surface |
| PHANTOM | Spiral persistence — maintains state across revolutions |
| SHADOW | Spiral observation — behavioral delta compression |
| VIPER | Precision fixes within any spoke |
| WRAITH | Lightweight spoke operations on mobile devices |
| SPECTER | Async event handling between spokes |

Fusion modes map to cross-spoke operations:
- **SHERLOCK-SUPERNOVA** = evidence spoke discovers smoking gun → full-system sweep
- **CORE-THINK AMPLIFIED** = hub synthesizes cross-spoke legal analysis
- **SONIC-BODYBUILDER** = massive data processing feeding all spokes simultaneously

---

## Evolution

The Spiral Engine is not static. It evolves:

1. **New spokes** can be added (e.g., Media/Public spoke, Congressional spoke)
2. **New pistons** can be attached to any spoke (new skills = new pistons)
3. **The spiral tightens** — each revolution requires fewer resources as
   knowledge compounds and patterns are recognized
4. **MORPHEUS** — the personalization engine ensures the spiral adapts
   to Casey's evolving needs without explicit reconfiguration

This is the architecture. Everything conforms to it.
