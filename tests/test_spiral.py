"""Test suite for Spiral Engine solution."""
import unittest
from spiral_engine import SpiralEngine

class TestSpiralEngine(unittest.TestCase):

    def test_spiral_revolution(self):
        engine = SpiralEngine()
        res = engine.log_revolution("Helix Alpha", "Executed compound matrix tick")
        
        self.assertEqual(res["status"], "SPIRAL_REVOLUTION_COMPOUNDED")
        self.assertEqual(res["revolution"], 1)

if __name__ == "__main__":
    unittest.main()
