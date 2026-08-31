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

    def export_revolutions(self) -> Dict[str, Any]:
        """Export the cryptographically chained adaptive revolution history."""
        return self.controller.export()

