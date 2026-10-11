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

    def test_require_existing_refuses_missing_journal_without_creating_one(self):
        missing = Path(self.tmp.name) / 'never-created.jsonl'
        with self.assertRaises((JournalIntegrityError, FileNotFoundError)):
            ContinuityJournal(missing, 'mission-1', 'Get a paid AI engineering role',
                              terminal_outcome='PAID_EMPLOYMENT', require_existing=True)
        self.assertFalse(missing.exists())

    def test_require_existing_refuses_empty_history_without_bootstrapping(self):
        self.file.write_text('')
        with self.assertRaises(JournalIntegrityError):
            ContinuityJournal(self.file, 'mission-1', 'Get a paid AI engineering role',
                              terminal_outcome='PAID_EMPLOYMENT', require_existing=True)
        self.assertEqual(self.file.read_bytes(), b'')

    def test_require_existing_preserves_original_authenticated_chain(self):
        key = b'independent-protected-test-secret-1234'
        target = Path(self.tmp.name) / 'signed.jsonl'
        written = ContinuityJournal(target, 'signed-1', 'Mission remains operational',
                                    terminal_outcome='REAL_OUTCOME', integrity_key=key)
        written.correct('Never claim completion from a draft')
        before = target.read_bytes()
        recovered = ContinuityJournal(target, 'signed-1', 'Mission remains operational',
                                      terminal_outcome='REAL_OUTCOME', integrity_key=key,
                                      require_existing=True)
        self.assertEqual(target.read_bytes(), before)
        self.assertEqual(recovered.corrections, ['Never claim completion from a draft'])

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
            outcome_evidence=outcome,
            verify_outcome=lambda ev: ev.receipt == 'employer:contract-456')
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
        r2 = runner.run(['login', 'new-provider'], lambda r: (seen.append(r), RouteResult(True, 'submitted', 'employer:receipt'))[1], lambda j: OutcomeEvidence('PAID_EMPLOYMENT', 'employment:contract') if j.route_succeeded('new-provider') else None,
                        verify_outcome=lambda ev: ev.receipt == 'employment:contract')
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

    def test_malformed_scalar_journal_fails_with_integrity_error(self):
        self.file.write_text('1\n')
        with self.assertRaises(JournalIntegrityError):
            ContinuityJournal(self.file, 'mission-1', 'Get a paid AI engineering role', terminal_outcome='PAID_EMPLOYMENT')

    def test_replaced_journal_does_not_allow_injected_mission(self):
        other_file = Path(self.tmp.name) / 'other.jsonl'
        other = ContinuityJournal(other_file, 'different', 'Different goal', terminal_outcome='DIFFERENT')
        self.file.write_bytes(other_file.read_bytes())
        with self.assertRaises(JournalIntegrityError):
            self.journal.verify_fact('foo', 'bar', source='provider:abc')

    def test_rollback_of_existing_journal_detected_on_append(self):
        self.journal.verify_fact('fact', 'value', source='provider:first')
        self.journal.checkpoint('next')
        self.file.write_text('\n'.join(self.file.read_text().splitlines()[:1]) + '\n')
        with self.assertRaises(JournalIntegrityError):
            self.journal.correct('Do not lose my progress')

    def test_whitespace_receipts_do_not_satisfy_completion(self):
        with self.assertRaises(ValueError):
            self.journal.complete('   ', outcome_type='PAID_EMPLOYMENT')
        self.journal.define_task('a', 'a')
        with self.assertRaises(ValueError):
            self.journal.complete_task('a', '  ')

    def test_blank_outcome_evidence_does_not_complete_or_abort_routes(self):
        completed = MissionRunner(self.journal).run(
            routes=['one', 'two'],
            perform=lambda _: RouteResult(True, receipt='provider:route'),
            outcome_evidence=lambda _: OutcomeEvidence('PAID_EMPLOYMENT', '   '),
        )
        self.assertEqual(completed.state, 'RESUMABLE')
        self.assertEqual(completed.attempted, ('one', 'two'))
        self.assertFalse(self.journal.is_complete)

    def test_mismatched_outcome_evidence_does_not_end_mission(self):
        result = MissionRunner(self.journal).run(
            routes=['ats', 'recruiter'],
            perform=lambda _: RouteResult(True, receipt='provider:receipt'),
            outcome_evidence=lambda _: OutcomeEvidence('APPLICATION_RECEIVED', 'provider:receipt'),
        )
        self.assertEqual(result.state, 'RESUMABLE')
        self.assertFalse(self.journal.is_complete)

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