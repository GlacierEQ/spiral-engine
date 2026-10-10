"""Outcome-first Spiral Engine continuity and recovery regression tests."""
import tempfile
import unittest
from pathlib import Path

from src.continuity import ContinuityJournal, MissionRunner, RouteResult, OutcomeEvidence, JournalIntegrityError


class ContinuityTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.file = Path(self.tmp.name) / 'mission.jsonl'
        self.journal = ContinuityJournal(self.file, 'mission-1', 'Get a paid AI engineering role', terminal_outcome='PAID_EMPLOYMENT')

    def test_verified_fact_survives_restart_and_unverified_conflict(self):
        self.journal.verify_fact('application', 'received', source='employer:receipt-123', revision='A')
        self.journal.note_conflict('application', 'maybe rejected', source='assistant-summary')
        recovered = ContinuityJournal(self.file, 'mission-1', 'Get a paid AI engineering role', terminal_outcome='PAID_EMPLOYMENT')
        self.assertEqual(recovered.fact('application')['value'], 'received')
        self.assertTrue(recovered.conflicts('application'))
        self.assertFalse(recovered.is_complete)

    def test_supersession_requires_source_receipt(self):
        self.journal.verify_fact('status', 'under_review', source='employer:1', revision='v1')
        with self.assertRaises(ValueError):
            self.journal.supersede_fact('status', 'offered', source='')
        self.journal.supersede_fact('status', 'offered', source='employer:2', revision='v2')
        self.assertEqual(self.journal.fact('status')['value'], 'offered')
        self.assertEqual(len(self.journal.fact_history('status')), 2)

    def test_hash_chain_rejects_corrupted_history(self):
        self.journal.verify_fact('a', 1, source='source:1')
        text = self.file.read_text()
        self.file.write_text(text.replace('"value":1', '"value":2'))
        with self.assertRaises(JournalIntegrityError):
            ContinuityJournal(self.file, 'mission-1', 'Get a paid AI engineering role', terminal_outcome='PAID_EMPLOYMENT')

    def test_correction_and_resume_cursor_survive_restart(self):
        self.journal.correct('Never confuse a prepared application with submitted.')
        self.journal.checkpoint('ats:challenge', detail='Route A cannot continue; seek independent route')
        recovered = ContinuityJournal(self.file, 'mission-1', 'Get a paid AI engineering role', terminal_outcome='PAID_EMPLOYMENT')
        self.assertIn('Never confuse', recovered.corrections[0])
        self.assertEqual(recovered.cursor, 'ats:challenge')

    def test_failed_route_reroutes_and_outcome_receipt_completes(self):
        attempts = []
        def perform(route):
            attempts.append(route)
            if route == 'greenhouse':
                return RouteResult(success=False, detail='login challenge')
            return RouteResult(success=True, receipt='employer:application-456')
        def outcome(journal):
            return OutcomeEvidence('PAID_EMPLOYMENT', 'employer:contract-456') if journal.route_succeeded('alternate-ats') else None
        result = MissionRunner(self.journal).run(
            routes=['greenhouse', 'alternate-ats'], perform=perform,
            outcome_evidence=outcome)
        self.assertEqual(attempts, ['greenhouse', 'alternate-ats'])
        self.assertEqual(result.state, 'COMPLETE')
        self.assertTrue(ContinuityJournal(self.file, 'mission-1', 'Get a paid AI engineering role', terminal_outcome='PAID_EMPLOYMENT').is_complete)

    def test_successful_activity_does_not_imply_mission_completion(self):
        result = MissionRunner(self.journal).run(
            routes=['create-resume'],
            perform=lambda _: RouteResult(success=True, receipt='github:commit-1'),
            outcome_evidence=lambda _: None)
        self.assertEqual(result.state, 'RESUMABLE')
        self.assertFalse(self.journal.is_complete)
        self.assertEqual(self.journal.cursor, 'route-discovery')

    def test_retry_after_new_route_not_repeat_failed_route(self):
        seen = []
        runner = MissionRunner(self.journal)
        r1 = runner.run(['login'], lambda r: (seen.append(r), RouteResult(False, 'OTP missing'))[1], lambda _: None)
        self.assertEqual(r1.state, 'RESUMABLE')
        r2 = runner.run(['login', 'new-provider'], lambda r: (seen.append(r), RouteResult(True, 'submitted', 'employer:receipt'))[1], lambda j: OutcomeEvidence('PAID_EMPLOYMENT', 'employment:contract') if j.route_succeeded('new-provider') else None)
        self.assertEqual(seen, ['login', 'new-provider'])
        self.assertEqual(r2.state, 'COMPLETE')

    def test_no_outcome_without_provider_receipt(self):
        with self.assertRaises(ValueError):
            self.journal.complete('', outcome_type='PAID_EMPLOYMENT')
        self.assertFalse(self.journal.is_complete)

    def test_application_receipt_is_not_paid_job_completion(self):
        with self.assertRaises(ValueError):
            self.journal.complete('greenhouse:received', outcome_type='APPLICATION_RECEIVED')
        self.assertFalse(self.journal.is_complete)

    def test_untyped_outcome_does_not_complete_mission(self):
        with self.assertRaises((TypeError, ValueError)):
            self.journal.complete('untyped receipt')
        self.assertFalse(self.journal.is_complete)

    def test_mission_identity_is_immutable(self):
        with self.assertRaises(JournalIntegrityError):
            ContinuityJournal(self.file, 'different-mission', 'Get a paid AI engineering role', terminal_outcome='PAID_EMPLOYMENT')

    def test_durable_tree_needs_task_receipt(self):
        self.journal.define_task('application', 'Submit to employer', parent=None)
        self.journal.define_task('confirmation', 'Read employer confirmation', parent='application')
        with self.assertRaises(ValueError):
            self.journal.complete_task('confirmation', '')
        self.journal.complete_task('confirmation', 'employer:application-12')
        self.assertTrue(self.journal.task_is_complete('confirmation'))
        self.assertFalse(self.journal.is_complete)


if __name__ == '__main__':
    unittest.main()