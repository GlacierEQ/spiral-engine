"""
Spiral Engine — Production Compound Revolution & Intelligence Scaling Engine

Key Innovations:
  1. Compound Revolution Tracker: Logs and scales intelligence states across Double Helix iterations.
  2. Memory Matrix Router: Zero-loss context logging for APEX agentic state tracking.
"""

from typing import Dict, Any
import time

try:
    from .revolution_controller import (
        Impact,
        Intervention,
        PromotionEvidence,
        QualityState,
        RevolutionReceipt,
        SpiralController,
        SpiralPolicy,
        decide_revolution,
        verify_receipt_chain,
    )
except ImportError:  # direct module import compatibility
    from revolution_controller import (
        Impact,
        Intervention,
        PromotionEvidence,
        QualityState,
        RevolutionReceipt,
        SpiralController,
        SpiralPolicy,
        decide_revolution,
        verify_receipt_chain,
    )

class SpiralEngine:
    """Manages compound revolution iterations and APEX memory state scaling."""

    def __init__(self):
        self.revolution_count = 0
        self.revolution_history = []
        self.controller = SpiralController()

    def log_revolution(self, helix: str, summary: str) -> Dict[str, Any]:
        """Logs and compounds a spiral revolution tick."""
        self.revolution_count += 1
        entry = {
            "revolution": self.revolution_count,
            "helix": helix,
            "summary": summary,
            "timestamp": time.time()
        }
        self.revolution_history.append(entry)
        return {
            "revolution": self.revolution_count,
            "status": "SPIRAL_REVOLUTION_COMPOUNDED",
            "entry": entry
            }

    def evaluate_revolution(
        self,
        before: QualityState,
        after: QualityState,
        intervention: Intervention,
        promotion: PromotionEvidence | None = None,
    ) -> RevolutionReceipt:
        """Record one measured adaptive revolution through the v2 controller."""
        receipt = self.controller.record(before, after, intervention, promotion)
        self.revolution_count = max(self.revolution_count, receipt.revolution)
        self.revolution_history.append({
            "revolution": receipt.revolution,
            "status": receipt.signal,
            "summary": receipt.reason,
            "receipt_sha256": receipt.receipt_sha256,
        })
        return receipt

    @staticmethod
    def _pyramid_outcome_verifier(journal, verify_outcome, pyramid_state,
                                  pyramid_verify, pyramid_source_dir):
        """Bind native outcome checks to the exact shared Pyramid terminal proof."""
        if pyramid_state is None and pyramid_verify is None:
            return verify_outcome
        if not callable(pyramid_state) or not callable(pyramid_verify) or not callable(verify_outcome):
            raise ValueError("Pyramid requires state, independent proof and outcome callbacks")
        import json
        from pathlib import Path
        from .progressive_pyramid_source import resolve_pyramid_source, validate_pyramid_run
        lock = json.loads((Path(__file__).resolve().parents[1] /
                           "config/progressive_pyramid_source_lock.json").read_text())
        state = resolve_pyramid_source(lock, source_dir=pyramid_source_dir)
        if state["status"] != "LOADED":
            raise ValueError("Pyramid contract source not verified: " + state["status"])
        initial = pyramid_state()
        if (not isinstance(initial, dict)
                or initial.get("mission_id") != journal.mission_id
                or initial.get("original_outcome") != journal.objective
                or initial.get("protocol") != lock["schema_id"]):
            raise ValueError("Pyramid cannot replace original mission identity")
        def bound(evidence):
            if verify_outcome(evidence) is not True:
                return False
            current = pyramid_state()
            if not isinstance(current, dict):
                return False
            center = current.get("center_point", {})
            if not isinstance(center, dict) or center.get("status") != "MISSION_COMPLETE":
                return False
            proofs = center.get("outcome_proofs", [])
            if not isinstance(proofs, list) or not any(
                isinstance(item, dict) and item.get("source_ref") == evidence.receipt
                for item in proofs
            ):
                return False
            return not validate_pyramid_run(
                current, lock, source_dir=pyramid_source_dir, verifier=pyramid_verify)
        return bound

    def run_mission(
        self,
        journal,
        *,
        routes,
        evaluate,
        propose,
        execute,
        outcome_evidence,
        verify_outcome,
        max_attempts: int = 20,
        improvement_contract=None,
        observe_improvement=None,
        verify_improvement=None,
        pyramid_state=None,
        pyramid_verify=None,
        pyramid_source_dir=None,
    ):
        """Run the ORIGINAL measured controller inside durable mission execution.

        Quality target attainment is a per-revolution observation; it is not a
        terminal human outcome. The existing controller, scoring, and receipt
        algorithm remain authoritative for feedback, while the continuity
        journal governs mission completion and cross-session continuation.
        """
        try:
            from .continuity import MissionRunner, RouteResult
        except ImportError:
            from continuity import MissionRunner, RouteResult

        from .improvement import ImprovementContract, evaluate_improvement
        terminal_verifier = verify_outcome
        terminal_verifier = self._pyramid_outcome_verifier(
            journal, verify_outcome, pyramid_state, pyramid_verify, pyramid_source_dir)
        improvement_args = (improvement_contract, observe_improvement, verify_improvement)
        if any(value is not None for value in improvement_args):
            if (not isinstance(improvement_contract, ImprovementContract)
                    or not callable(observe_improvement)
                    or not callable(verify_improvement)):
                raise ValueError("improvement binding requires contract, observations and independent verifier")
            expected = (journal.mission_id, journal.objective, journal.terminal_outcome)
            actual = (improvement_contract.mission_id, improvement_contract.objective,
                      improvement_contract.terminal_outcome)
            if expected != actual:
                raise ValueError("improvement contract must preserve active mission identity")

        history = journal.revolution_receipts
        current_hashes = tuple(r.receipt_sha256 for r in self.controller.receipts)
        stored_hashes = tuple(r.receipt_sha256 for r in history)
        if current_hashes:
            if current_hashes != stored_hashes:
                raise ValueError("engine and mission histories differ; refusing silent replacement")
        else:
            self.controller.restore(history)

        def perform_route(route):
            before_improvement = observe_improvement() if improvement_contract is not None else None
            if improvement_contract is not None:
                from .improvement import ImprovementObservation
                inherited_keys = {
                    event["data"]["key"] for event in journal.events
                    if event["kind"] in {"verified_fact", "superseded_fact"}
                }
                if (not isinstance(before_improvement, ImprovementObservation)
                        or not inherited_keys.issubset(set(before_improvement.verified_facts))):
                    raise ValueError("improvement observation omitted source-verified journal facts")
            before = evaluate()
            intervention = propose(route, before)
            if not isinstance(intervention, Intervention):
                raise TypeError("mission proposer must return original Spiral Intervention")
            outcome = execute(route, intervention)
            if not isinstance(outcome, RouteResult):
                raise TypeError("mission executor must return RouteResult")
            after = evaluate()
            receipt = self.controller.record(before, after, intervention)
            journal.append_revolution(receipt)
            if improvement_contract is not None:
                after_improvement = observe_improvement()
                from .improvement import ImprovementObservation
                inherited_after = {
                    event["data"]["key"] for event in journal.events
                    if event["kind"] in {"verified_fact", "superseded_fact"}
                }
                if (not isinstance(after_improvement, ImprovementObservation)
                        or not inherited_after.issubset(set(after_improvement.verified_facts))):
                    raise ValueError("improvement observation omitted source-verified journal facts")
                assessment = evaluate_improvement(
                    improvement_contract, before_improvement, after_improvement,
                    verify_evidence=verify_improvement,
                )
                journal.record_improvement(assessment)
            self.revolution_count = max(self.revolution_count, receipt.revolution)
            self.revolution_history.append({
                "revolution": receipt.revolution,
                "route": route,
                "feedback_signal": receipt.signal,
                "receipt_sha256": receipt.receipt_sha256,
                "mission_complete": False,
            })
            return outcome

        result = MissionRunner(journal).run(
            routes, perform_route, outcome_evidence,
            max_attempts=max_attempts, verify_outcome=terminal_verifier,
        )
        # Terminal outcome is journal-and-provider proof, never the quality
        # controller's independent notion of a completed quality revolution.
        return result

    def export_revolutions(self) -> Dict[str, Any]:
        """Export the cryptographically chained adaptive revolution history."""
        return self.controller.export()

