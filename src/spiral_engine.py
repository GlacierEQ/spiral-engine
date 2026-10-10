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

        history = journal.revolution_receipts
        current_hashes = tuple(r.receipt_sha256 for r in self.controller.receipts)
        stored_hashes = tuple(r.receipt_sha256 for r in history)
        if current_hashes:
            if current_hashes != stored_hashes:
                raise ValueError("engine and mission histories differ; refusing silent replacement")
        else:
            self.controller.restore(history)

        def perform_route(route):
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
            max_attempts=max_attempts, verify_outcome=verify_outcome,
        )
        # Terminal outcome is journal-and-provider proof, never the quality
        # controller's independent notion of a completed quality revolution.
        return result

    def export_revolutions(self) -> Dict[str, Any]:
        """Export the cryptographically chained adaptive revolution history."""
        return self.controller.export()

