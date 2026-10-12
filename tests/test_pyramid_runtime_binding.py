"""Pyramid must reject false mission completion in the real Spiral controller."""
import tempfile
import unittest
from pathlib import Path
from src import SpiralEngine
from src.continuity import ContinuityJournal, OutcomeEvidence

class PyramidMissionBindingTests(unittest.TestCase):
    def test_unpaired_binding_rejected_before_any_work(self):
        with tempfile.TemporaryDirectory() as td:
            journal=ContinuityJournal(Path(td)/"journal.jsonl","mission-1","Real outcome",terminal_outcome="REAL")
            with self.assertRaises(ValueError):
                SpiralEngine._pyramid_outcome_verifier(
                    journal,lambda receipt: True,lambda: {},None,None)
            self.assertFalse(journal.is_complete)

    def test_no_pyramid_binding_preserves_existing_strict_verifier(self):
        verifier=lambda evidence: evidence.receipt=="native:1"
        result=SpiralEngine._pyramid_outcome_verifier(None,verifier,None,None,None)
        self.assertIs(result,verifier)

if __name__=="__main__":unittest.main()

class LiveSourceAdoptionTests(unittest.TestCase):
    def test_pinned_source_enforces_center_point(self):
        import json
        root=Path.home()/".agents/skills/progressive-pyramid"
        if not root.is_dir():
            self.skipTest("canonical Skill is not installed on this host")
        from src.progressive_pyramid_source import resolve_pyramid_source
        repo=Path(__file__).resolve().parents[1]
        lock=json.loads((repo/"config/progressive_pyramid_source_lock.json").read_text())
        self.assertEqual(resolve_pyramid_source(lock,source_dir=root)["status"],"LOADED")
        with tempfile.TemporaryDirectory() as td:
            journal=ContinuityJournal(Path(td)/"journal.jsonl",
                "mission-1","Original real-world mission",terminal_outcome="PROVIDER_OUTCOME")
            stages=[]
            last=None
            for name,ver in [("corner_1_context","V1"),("corner_2_objective","V2"),
                              ("corner_3_constraints","V3"),("corner_4_resources","V4")]:
                ref=f"source:{ver}"
                stages.append({"stage":name,"version":ver,"artifact_ref":ref,
                               "inherits":last,"verified_gains":["known-gain"]})
                last=ref
            run={"protocol":lock["schema_id"],"mission_id":journal.mission_id,
                 "original_outcome":journal.objective,"recovered_sources":["source:original"],
                 "acceptance_criteria":["external-result"],"stages":stages,
                 "center_point":{"status":"ACTIVE","outcome_proofs":[]}}
            state=lambda:run
            verified=lambda p: p.receipt=="provider:finished"
            proof=lambda criterion,ref: criterion=="external-result" and ref=="provider:finished"
            gate=SpiralEngine._pyramid_outcome_verifier(journal,verified,state,proof,root)
            outcome=OutcomeEvidence("PROVIDER_OUTCOME","provider:finished")
            self.assertFalse(gate(outcome),"intermediate work must never complete the mission")
            run["center_point"]={"status":"MISSION_COMPLETE",
              "outcome_proofs":[{"criterion":"external-result","source_ref":"self:claim"}]}
            self.assertFalse(gate(outcome),"self-attested proof must not complete mission")
            run["center_point"]["outcome_proofs"][0]["source_ref"]="provider:finished"
            self.assertTrue(gate(outcome),"matching source-native proof may pass both verification boundaries")
            self.assertFalse(gate(OutcomeEvidence("PROVIDER_OUTCOME","assistant:draft")))

class RealMissionExecutionTests(unittest.TestCase):
    def test_spiral_completes_only_after_both_center_and_provider_evidence(self):
        import json
        from src import QualityState, Impact, Intervention
        from src.continuity import RouteResult
        root=Path.home()/".agents/skills/progressive-pyramid"
        if not root.is_dir():
            self.skipTest("canonical installed Skill unavailable")
        lock=json.loads((Path(__file__).resolve().parents[1]/
                        "config/progressive_pyramid_source_lock.json").read_text())
        with tempfile.TemporaryDirectory() as td:
            journal=ContinuityJournal(Path(td)/"journal.jsonl","mission-test","Obtain actual delivery",
                terminal_outcome="DELIVERED")
            previous=None
            stages=[]
            for name,version in [("corner_1_context","V1"),("corner_2_objective","V2"),
                                 ("corner_3_constraints","V3"),("corner_4_resources","V4")]:
                ref=f"source:{version}"
                stages.append({"stage":name,"version":version,"artifact_ref":ref,
                               "inherits":previous,"verified_gains":["valid-baseline"]})
                previous=ref
            state={"run":{"protocol":lock["schema_id"],"mission_id":journal.mission_id,
                "original_outcome":journal.objective,"recovered_sources":["source:prior"],
                "acceptance_criteria":["delivered"],"stages":stages,
                "center_point":{"status":"ACTIVE"}},"score":8.0}
            def execute(route,work):
                state["score"]=9.0
                state["run"]["center_point"]={
                    "status":"MISSION_COMPLETE",
                    "outcome_proofs":[{"criterion":"delivered","source_ref":"provider:delivery"}]}
                return RouteResult(True,receipt="provider:delivery")
            result=SpiralEngine().run_mission(
                journal, routes=["deliver-via-provider"],
                evaluate=lambda: QualityState(state["score"],state["score"],
                                               {"correctness":state["score"]},
                                               fingerprint=str(state["score"])),
                propose=lambda route, before: Intervention(
                    route,"Perform real delivery",Impact(.7,.7,.7,.7,.7,.7,.2,.2,0)),
                execute=execute,
                outcome_evidence=lambda j: OutcomeEvidence("DELIVERED","provider:delivery")
                    if j.route_succeeded("deliver-via-provider") else None,
                verify_outcome=lambda e:e.outcome_type=="DELIVERED" and e.receipt=="provider:delivery",
                pyramid_state=lambda:state["run"],
                pyramid_verify=lambda k,r:k=="delivered" and r=="provider:delivery",
                pyramid_source_dir=root,
            )
            self.assertEqual(result.state,"COMPLETE")
            self.assertTrue(journal.is_complete)
