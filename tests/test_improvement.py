"""Mission-bound definition of improvement: real progress, retained gains, independently verified."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src import (
    ImprovementContract,
    ImprovementCriterion,
    ImprovementObservation,
    SpiralEngine,
    evaluate_improvement,
    Impact,
    Intervention,
    QualityState,
)
from src.continuity import ContinuityJournal, RouteResult


def contract():
    return ImprovementContract(
        mission_id="employment",
        objective="Obtain paid AI engineering employment",
        terminal_outcome="PAID_EMPLOYMENT",
        criteria=(
            ImprovementCriterion("outcome_progress", "outcome"),
            ImprovementCriterion("engineering_capability", "capability"),
            ImprovementCriterion("memory_integrity", "integrity"),
        ),
        protected_capabilities=("github", "context-recovery"),
    )


def observation(outcome=2.0, capability=7.0, memory=8.0, *,
                capabilities=("github", "context-recovery"), facts=("verified-application",),
                evidence=None):
    return ImprovementObservation(
        measures={
            "outcome_progress": outcome,
            "engineering_capability": capability,
            "memory_integrity": memory,
        },
        capabilities=capabilities,
        verified_facts=facts,
        evidence={} if evidence is None else evidence,
    )


def native_verify(key, ref, old, new):
    return key == "outcome_progress" and ref == "employer:receipt-actual" and new > old


class ImprovementContractTests(unittest.TestCase):
    def test_outcome_progress_is_improvement_only_with_native_evidence(self):
        receipt = evaluate_improvement(
            contract(),
            observation(),
            observation(outcome=5.0, evidence={"outcome_progress": "employer:receipt-actual"}),
            verify_evidence=native_verify,
        )
        self.assertEqual(receipt.state, "IMPROVED")
        self.assertEqual(receipt.improvements, ("outcome_progress",))
        self.assertTrue(receipt.verify())
        self.assertEqual(receipt.mission_id, "employment")

    def test_self_claimed_receipt_is_not_verified_improvement(self):
        receipt = evaluate_improvement(
            contract(), observation(),
            observation(outcome=9.9, evidence={"outcome_progress": "assistant:says-so"}),
            verify_evidence=native_verify,
        )
        self.assertEqual(receipt.state, "UNVERIFIED")
        self.assertNotEqual(receipt.state, "IMPROVED")

    def test_impressive_score_without_receipt_is_not_improvement(self):
        receipt = evaluate_improvement(
            contract(), observation(),
            observation(outcome=9.9),
            verify_evidence=native_verify,
        )
        self.assertEqual(receipt.state, "UNVERIFIED")

    def test_no_evidence_verifier_cannot_assert_real_progress(self):
        receipt = evaluate_improvement(
            contract(), observation(),
            observation(outcome=5.0, evidence={"outcome_progress": "employer:receipt-actual"}),
        )
        self.assertEqual(receipt.state, "UNVERIFIED")

    def test_loss_of_prior_capability_is_regression_despite_goal_gain(self):
        receipt = evaluate_improvement(
            contract(), observation(),
            observation(outcome=9.9, capabilities=("github",),
                        evidence={"outcome_progress": "employer:receipt-actual"}),
            verify_evidence=native_verify,
        )
        self.assertEqual(receipt.state, "REGRESSION")
        self.assertIn("context-recovery", receipt.lost_capabilities)

    def test_loss_of_verified_fact_is_regression_despite_goal_gain(self):
        receipt = evaluate_improvement(
            contract(), observation(),
            observation(outcome=9.9, facts=(),
                        evidence={"outcome_progress": "employer:receipt-actual"}),
            verify_evidence=native_verify,
        )
        self.assertEqual(receipt.state, "REGRESSION")
        self.assertIn("verified-application", receipt.lost_facts)

    def test_quality_regression_is_not_hidden_by_target_gain(self):
        receipt = evaluate_improvement(
            contract(), observation(),
            observation(outcome=5.0, memory=7.0,
                        evidence={"outcome_progress": "employer:receipt-actual"}),
            verify_evidence=native_verify,
        )
        self.assertEqual(receipt.state, "REGRESSION")
        self.assertIn("memory_integrity", receipt.regressions)

    def test_no_material_change_does_not_manufacture_improvement(self):
        receipt = evaluate_improvement(contract(), observation(), observation(),
                                       verify_evidence=native_verify)
        self.assertEqual(receipt.state, "NO_GAIN")

    def test_new_capability_requires_evidence_not_just_a_string(self):
        after = observation(capabilities=("github", "context-recovery", "new-deployment"),
                            evidence={"capability:new-deployment": "self:claim"})
        receipt = evaluate_improvement(
            contract(), observation(), after,
            verify_evidence=lambda key, ref, old, new: False,
        )
        self.assertEqual(receipt.state, "UNVERIFIED")

    def test_contract_rejects_blank_wrong_or_missing_objective_criteria(self):
        with self.assertRaises(ValueError):
            ImprovementContract("employment", "Obtain paid AI engineering employment",
                                "PAID_EMPLOYMENT",
                                (ImprovementCriterion("memory", "integrity"),))
        with self.assertRaises(ValueError):
            ImprovementCriterion("quality", "unknown")
        with self.assertRaises(ValueError):
            ImprovementObservation(measures={"outcome_progress": float("nan")})

    def test_missing_measure_is_rejected_not_silently_zeroed(self):
        with self.assertRaises(ValueError):
            evaluate_improvement(contract(), observation(),
                                 ImprovementObservation(measures={"outcome_progress": 8.0}),
                                 verify_evidence=native_verify)

    def test_mission_identity_guard_and_persistent_receipts(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "mission.jsonl"
            journal = ContinuityJournal(
                path, "employment", "Obtain paid AI engineering employment",
                terminal_outcome="PAID_EMPLOYMENT",
            )
            assessment = evaluate_improvement(
                contract(), observation(),
                observation(outcome=5.0, evidence={"outcome_progress": "employer:receipt-actual"}),
                verify_evidence=native_verify,
            )
            journal.record_improvement(assessment)
            recovered = ContinuityJournal(
                path, "employment", "Obtain paid AI engineering employment",
                terminal_outcome="PAID_EMPLOYMENT",
            )
            self.assertEqual(recovered.improvement_history[-1].digest, assessment.digest)
            self.assertTrue(recovered.improvement_history[-1].verify())
            self.assertFalse(recovered.is_complete)
            with self.assertRaises(ValueError):
                other = ImprovementContract(
                    "other-mission", contract().objective, contract().terminal_outcome,
                    contract().criteria,
                )
                journal.record_improvement(evaluate_improvement(
                    other, observation(), observation()))

    def test_engine_records_improvement_without_short_circuiting_terminal_outcome(self):
        with tempfile.TemporaryDirectory() as tmp:
            journal = ContinuityJournal(
                Path(tmp) / "mission.jsonl",
                "employment", "Obtain paid AI engineering employment",
                terminal_outcome="PAID_EMPLOYMENT",
            )
            current = {"quality": 8.0, "outcome": 2.0}
            def quality():
                n = current["quality"]
                return QualityState(n, n, {"correctness": n}, fingerprint=str(n))
            def execute(route, work):
                current["quality"] = 9.5
                current["outcome"] = 5.0
                return RouteResult(True, receipt="employer:receipt-actual")
            engine = SpiralEngine()
            result = engine.run_mission(
                journal,
                routes=("submit",),
                evaluate=quality,
                propose=lambda route, before: Intervention(
                    route, "Submit real application", Impact(.7,.7,.7,.7,.7,.7,.2,.2,0)),
                execute=execute,
                outcome_evidence=lambda journal: None,
                verify_outcome=lambda evidence: False,
                improvement_contract=contract(),
                observe_improvement=lambda: observation(
                    outcome=current["outcome"],
                    evidence={"outcome_progress": "employer:receipt-actual"}
                    if current["outcome"] > 2 else {}),
                verify_improvement=native_verify,
            )
            self.assertEqual(result.state, "RESUMABLE")
            self.assertEqual(engine.controller.receipts[-1].signal, "COMPLETE")
            self.assertEqual(journal.improvement_history[-1].state, "IMPROVED")
            self.assertFalse(journal.is_complete)

    def test_incomplete_improvement_configuration_rejected_before_mutation(self):
        with tempfile.TemporaryDirectory() as tmp:
            journal = ContinuityJournal(
                Path(tmp) / "mission.jsonl",
                "employment", "Obtain paid AI engineering employment",
                terminal_outcome="PAID_EMPLOYMENT",
            )
            attempts = []
            with self.assertRaises(ValueError):
                SpiralEngine().run_mission(
                    journal, routes=("submit",),
                    evaluate=lambda: None, propose=lambda r, s: None,
                    execute=lambda r, i: attempts.append(r),
                    outcome_evidence=lambda j: None,
                    verify_outcome=lambda ev: False,
                    improvement_contract=contract(),
                )
            self.assertEqual(attempts, [])


if __name__ == "__main__":
    unittest.main()
