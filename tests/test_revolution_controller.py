from __future__ import annotations

import unittest

from src.revolution_controller import (
    Impact,
    Intervention,
    PromotionEvidence,
    QualityState,
    SpiralController,
    SpiralPolicy,
    decide_revolution,
    verify_receipt_chain,
)


def state(overall, floor, *, fingerprint="", **dimensions):
    return QualityState(
        overall=overall,
        critical_floor=floor,
        dimensions=dimensions or {
            "correctness": overall,
            "testing": overall,
            "security": floor,
            "semantic_placement": floor,
        },
        fingerprint=fingerprint,
    )


def intervention(name="x"):
    return Intervention(
        intervention_id=name,
        title="measured improvement",
        impact=Impact(
            near_term=.6,
            mid_term=.7,
            far_term=.8,
            capability_gain=.7,
            stability_gain=.8,
            reversibility=.9,
            risk=.2,
            effort=.3,
            complexity_delta=.1,
        ),
    )


class RevolutionControllerTests(unittest.TestCase):
    def test_continue_on_balanced_progress(self):
        receipt = decide_revolution(
            revolution=1,
            before=state(7.8, 7.2),
            after=state(8.2, 7.7),
            intervention=intervention(),
        )
        self.assertEqual(receipt.signal, "CONTINUE")
        self.assertTrue(receipt.verify())
        self.assertGreater(receipt.score_delta, 0)

    def test_complete_requires_overall_and_critical_floor(self):
        almost = decide_revolution(
            revolution=1,
            before=state(8.7, 8.4),
            after=state(9.2, 8.4),
            intervention=intervention(),
        )
        self.assertNotEqual(almost.signal, "COMPLETE")

        done = decide_revolution(
            revolution=1,
            before=state(8.7, 8.4),
            after=state(9.2, 8.7),
            intervention=intervention(),
        )
        self.assertEqual(done.signal, "COMPLETE")

    def test_local_gain_cannot_hide_critical_regression(self):
        before = state(
            8.4, 8.0,
            correctness=8.4,
            testing=8.2,
            security=8.0,
            semantic_placement=8.0,
        )
        after = state(
            8.7, 7.1,
            correctness=9.0,
            testing=8.5,
            security=7.1,
            semantic_placement=8.2,
        )
        receipt = decide_revolution(
            revolution=1,
            before=before,
            after=after,
            intervention=intervention(),
        )
        self.assertEqual(receipt.signal, "REVISE")
        self.assertIn("security", receipt.critical_regressions)

    def test_promotion_requires_full_evidence(self):
        before = state(8.0, 7.8)
        after = state(8.5, 8.2)

        weak = decide_revolution(
            revolution=1,
            before=before,
            after=after,
            intervention=intervention(),
            promotion=PromotionEvidence(
                required=True,
                execution_ready=True,
                behavioral_parity=True,
                rollback_ready=True,
                explicit_interface=False,
                benchmark_gain=.20,
                interface_cost=.05,
            ),
        )
        self.assertEqual(weak.signal, "CONTINUE")

        strong = decide_revolution(
            revolution=1,
            before=before,
            after=after,
            intervention=intervention(),
            promotion=PromotionEvidence(
                required=True,
                execution_ready=True,
                behavioral_parity=True,
                rollback_ready=True,
                explicit_interface=True,
                benchmark_gain=.20,
                interface_cost=.05,
            ),
        )
        self.assertEqual(strong.signal, "PROMOTE")
        self.assertTrue(strong.promotion_ready)

    def test_stagnation_becomes_constraint(self):
        controller = SpiralController(SpiralPolicy(stagnation_limit=2))
        before = state(7.0, 7.0, fingerprint="same")
        after = state(7.0, 7.0, fingerprint="same")

        first = controller.record(before, after, intervention("one"))
        second = controller.record(after, after, intervention("two"))

        self.assertEqual(first.signal, "REVISE")
        self.assertEqual(second.signal, "CONSTRAINED")

    def test_receipts_form_verifiable_chain(self):
        controller = SpiralController()
        a = state(7.0, 7.0, fingerprint="a")
        b = state(7.5, 7.4, fingerprint="b")
        c = state(8.0, 7.9, fingerprint="c")

        r1 = controller.record(a, b, intervention("one"))
        r2 = controller.record(b, c, intervention("two"))

        self.assertEqual(r2.previous_receipt_sha256, r1.receipt_sha256)
        self.assertEqual(verify_receipt_chain(controller.receipts), (True, None))

    def test_run_compounds_until_complete(self):
        values = [
            state(7.0, 7.0, fingerprint="a"),
            state(8.2, 8.0, fingerprint="b"),
            state(9.2, 8.7, fingerprint="c"),
        ]
        index = {"value": 0}

        def evaluate():
            return values[index["value"]]

        def propose(current):
            return intervention(f"rev-{index['value'] + 1}")

        def execute(_):
            index["value"] += 1
            return True

        controller = SpiralController()
        receipts = controller.run(
            evaluate=evaluate,
            propose=propose,
            execute=execute,
            max_revolutions=5,
        )

        self.assertEqual(receipts[-1].signal, "COMPLETE")
        self.assertEqual(len(receipts), 2)
        self.assertEqual(verify_receipt_chain(receipts), (True, None))

    def test_executor_decline_is_constrained_not_success(self):
        controller = SpiralController()
        current = state(7.0, 7.0, fingerprint="same")

        receipts = controller.run(
            evaluate=lambda: current,
            propose=lambda _: intervention("blocked"),
            execute=lambda _: False,
            max_revolutions=2,
        )

        self.assertEqual(receipts[-1].signal, "CONSTRAINED")
        self.assertIn("executor declined", receipts[-1].reason)


if __name__ == "__main__":
    unittest.main()
