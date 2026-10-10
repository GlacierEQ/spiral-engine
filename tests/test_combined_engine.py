"""Red/green contracts: existing feedback controller plus mission continuity form ONE engine."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from src import Impact, Intervention, QualityState, SpiralEngine, verify_receipt_chain
from src.continuity import ContinuityJournal, MissionRunner, OutcomeEvidence, RouteResult, JournalIntegrityError


def quality(n: float, fingerprint: str) -> QualityState:
    return QualityState(overall=n, critical_floor=min(n, 9.0),
                        dimensions={"correctness": n, "security": min(n, 9.0)},
                        fingerprint=fingerprint)


def intervention(route: str) -> Intervention:
    return Intervention(
        route, f"Execute {route}",
        Impact(.8, .8, .8, .8, .8, .9, .1, .2, .1))


class CombinedEngineTests(unittest.TestCase):
    def setUp(self):
        t = tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.path = Path(t.name) / "mission.jsonl"
        self.journal = ContinuityJournal(
            self.path, "job", "Obtain paid engineering employment",
            terminal_outcome="PAID_EMPLOYMENT")

    def test_main_controller_preserved_and_combined_mission_executes_past_quality_target(self):
        engine = SpiralEngine()
        state = {"value": quality(8.0, "start"), "offer": False}
        calls = []

        def execute(route, work):
            calls.append((route, work.intervention_id))
            if route == "research":
                state["value"] = quality(9.5, "excellent-research")
                return RouteResult(True, receipt="github:research-verified")
            if route == "apply":
                state["offer"] = True
                state["value"] = quality(9.6, "contract-signed")
                return RouteResult(True, receipt="employer:offer-verified")
            raise AssertionError("Unexpected route")

        def outcome(_):
            return (OutcomeEvidence("PAID_EMPLOYMENT", "employer:signed-contract")
                    if state["offer"] else None)

        first = engine.run_mission(
            self.journal, routes=["research"],
            evaluate=lambda: state["value"],
            propose=lambda route, _: intervention(route),
            execute=execute, outcome_evidence=outcome,
            verify_outcome=lambda ev: ev.receipt == "employer:signed-contract",
        )
        self.assertEqual(first.state, "RESUMABLE")
        self.assertFalse(self.journal.is_complete)
        self.assertEqual(len(engine.controller.receipts), 1)

        second = engine.run_mission(
            self.journal, routes=["research", "apply"],
            evaluate=lambda: state["value"],
            propose=lambda route, _: intervention(route),
            execute=execute, outcome_evidence=outcome,
            verify_outcome=lambda ev: ev.receipt == "employer:signed-contract",
        )
        self.assertEqual(second.state, "COMPLETE")
        self.assertEqual(calls, [("research", "research"), ("apply", "apply")])
        self.assertEqual(len(engine.controller.receipts), 2)
        self.assertEqual(verify_receipt_chain(engine.controller.receipts), (True, None))
        self.assertEqual(len(self.journal.revolution_receipts), 2)

    def test_revolution_history_restored_between_engine_processes(self):
        state = {"quality": quality(7.0, "before")}
        engine = SpiralEngine()

        def execute(route, _):
            state["quality"] = quality(8.0, "after")
            return RouteResult(True, receipt="provider:work")

        engine.run_mission(
            self.journal, routes=["route-1"],
            evaluate=lambda: state["quality"],
            propose=lambda route, _: intervention(route), execute=execute,
            outcome_evidence=lambda _: None, verify_outcome=lambda _: False,
        )
        resumed = SpiralEngine()
        resumed.run_mission(
            ContinuityJournal(self.path, "job", "Obtain paid engineering employment",
                              terminal_outcome="PAID_EMPLOYMENT"),
            routes=[], evaluate=lambda: state["quality"],
            propose=lambda route, _: intervention(route), execute=execute,
            outcome_evidence=lambda _: None, verify_outcome=lambda _: False,
        )
        self.assertEqual(len(resumed.controller.receipts), 1)
        self.assertEqual(verify_receipt_chain(resumed.controller.receipts), (True, None))

    def test_unverified_typed_receipt_cannot_complete(self):
        runner = MissionRunner(self.journal)
        result = runner.run(
            [], lambda _: RouteResult(True), lambda _: OutcomeEvidence("PAID_EMPLOYMENT", "fabricated"),
            verify_outcome=lambda _: False,
        )
        self.assertEqual(result.state, "RESUMABLE")
        self.assertFalse(self.journal.is_complete)

    def test_immutable_exposed_state(self):
        self.journal.verify_fact("status", {"value": "submitted"}, source="provider:received")
        event = self.journal.events[-1]
        event["kind"] = "mission_complete"
        event["data"]["value"] = {"value": "rejected"}
        fact = self.journal.fact("status")
        fact["value"]["value"] = "rejected"
        self.assertEqual(self.journal.fact("status")["value"], {"value": "submitted"})
        self.assertFalse(self.journal.is_complete)

    def test_stale_concurrent_writer_cannot_create_conflicting_verified_fact(self):
        other = ContinuityJournal(self.path, "job", "Obtain paid engineering employment",
                                  terminal_outcome="PAID_EMPLOYMENT")
        self.journal.verify_fact("status", "submitted", source="provider:1")
        with self.assertRaises((ValueError, JournalIntegrityError)):
            other.verify_fact("status", "rejected", source="provider:2")
        self.assertEqual(self.journal.fact("status")["value"], "submitted")

    def test_crash_does_not_automatically_replay_external_mutation(self):
        attempted = []
        def fail(route):
            attempted.append(route)
            raise RuntimeError("process interrupted immediately after provider submission")
        runner = MissionRunner(self.journal)
        try:
            runner.run(["submit"], fail, lambda _: None)
        except RuntimeError:
            pass
        runner.run(["submit"], lambda route: (attempted.append(route), RouteResult(True))[1],
                   lambda _: None)
        self.assertEqual(attempted, ["submit"])
        self.assertFalse(self.journal.is_complete)

    def test_infinite_repeated_route_stream_has_finite_scan_budget(self):
        from itertools import repeat
        n = 0
        def perform(route):
            nonlocal n
            n += 1
            return RouteResult(False, "no")
        result = MissionRunner(self.journal).run(
            repeat("same"), perform, lambda _: None, max_attempts=1,
        )
        self.assertEqual(n, 1)
        self.assertEqual(result.state, "RESUMABLE")


if __name__ == "__main__":
    unittest.main()
