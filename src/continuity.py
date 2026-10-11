"""Spiral Engine continuity: verified-state inheritance, alternate routes, durable outcome gates.

An authenticated source receipt establishes a fact until a later source-backed
supersession. Route friction never completes or permanently blocks a mission.
A quality score or a successful intermediate artifact never completes a mission.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import hmac
import json
import os
from pathlib import Path
from typing import Any, Callable, Iterable

try:
    import fcntl
except ImportError:  # pragma: no cover - Windows has no fcntl
    fcntl = None


class JournalIntegrityError(ValueError):
    """A persisted event stream has been modified or belongs to another mission."""


def _encoded(data: Any) -> bytes:
    return json.dumps(data, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')


def _digest(data: Any) -> str:
    return hashlib.sha256(_encoded(data)).hexdigest()


def _load(raw: str, integrity_key: bytes | None = None) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    previous = ''
    for index, line in enumerate(raw.splitlines(), 1):
        try:
            event = json.loads(line)
            auth_tag = event.pop('auth_tag', None)
            provided = event.pop('sha256')
            if (event['seq'] != index or event['previous_sha256'] != previous
                    or provided != _digest(event)):
                raise JournalIntegrityError(f'broken event chain at {index}')
            event['sha256'] = provided
            if integrity_key is not None:
                expected = hmac.new(integrity_key, _encoded(event), hashlib.sha256).hexdigest()
                if not isinstance(auth_tag, str) or not hmac.compare_digest(auth_tag, expected):
                    raise JournalIntegrityError(f'authentication failed at event {index}')
            elif auth_tag is not None:
                raise JournalIntegrityError('authenticated history requires original integrity key')
            if auth_tag is not None:
                event['auth_tag'] = auth_tag
        except (AttributeError, KeyError, TypeError, ValueError) as exc:
            raise JournalIntegrityError(f'invalid event at {index}') from exc
        events.append(event)
        previous = provided
    return events


class ContinuityJournal:
    """Append-only, SHA-linked mission journal with explicit source authority."""

    def __init__(self, path: Path | str, mission_id: str, objective: str, *,
                 terminal_outcome: str, integrity_key: bytes | None = None,
                 require_existing: bool = False):
        if not mission_id.strip() or not objective.strip() or not terminal_outcome.strip():
            raise ValueError('mission identity, objective and terminal outcome required')
        self.path = Path(path)
        self.mission_id = mission_id
        self.objective = objective
        self.terminal_outcome = terminal_outcome
        if integrity_key is not None and (not isinstance(integrity_key, bytes) or len(integrity_key) < 16):
            raise ValueError('journal authentication key must contain at least 16 bytes')
        self.integrity_key = integrity_key
        if require_existing:
            # A chat resume MUST NOT manufacture an empty replacement mission.
            # The caller owns pre-existing storage and a separately pinned head.
            if not self.path.is_file():
                raise JournalIntegrityError('required existing journal is missing')
            raw = self.path.read_text('utf-8')
            if not raw.strip():
                raise JournalIntegrityError('required existing journal is empty')
            self._events = _load(raw, self.integrity_key)
            if not self._events:
                raise JournalIntegrityError('required existing journal has no events')
        else:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self._events = _load(self.path.read_text('utf-8'), self.integrity_key) if self.path.exists() else []
        if self._events:
            first = self._events[0]
            if (first['kind'] != 'mission' or first['data'] !=
                    {'mission_id': mission_id, 'objective': objective, 'terminal_outcome': terminal_outcome}):
                raise JournalIntegrityError('mission identity mismatch')
        else:
            if require_existing:
                raise JournalIntegrityError('existing journal cannot be bootstrapped during recovery')
            self._append('mission', mission_id=mission_id, objective=objective, terminal_outcome=terminal_outcome)

    def _append(self, kind: str, **data: Any) -> dict[str, Any]:
        if fcntl is None:
            raise OSError('safe concurrent journal append requires fcntl; no unsafe unlocked fallback')
        with self.path.open('a+', encoding='utf-8') as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                handle.seek(0)
                current = _load(handle.read(), self.integrity_key)
                expected = {'mission_id': self.mission_id,
                            'objective': self.objective,
                            'terminal_outcome': self.terminal_outcome}
                if current and (current[0]['kind'] != 'mission' or
                                current[0]['data'] != expected):
                    raise JournalIntegrityError('journal identity changed')
                if (len(current) < len(self._events) or
                    any(old['sha256'] != actual['sha256']
                        for old, actual in zip(self._events, current))):
                    raise JournalIntegrityError('journal lost or replaced previously observed events')
                if kind == 'mission' and current:
                    self._events = current
                    return current[0]
                if kind == 'verified_fact':
                    existing = [e for e in current if e['kind'] in {'verified_fact', 'superseded_fact'}
                                and e['data']['key'] == data['key']]
                    if existing:
                        if existing[-1]['data']['value'] != data['value']:
                            raise ValueError('verified facts require explicit supersession')
                        self._events = current
                        return existing[-1]
                if kind == 'superseded_fact':
                    history = [e for e in current if e['kind'] in {'verified_fact', 'superseded_fact'}
                               and e['data']['key'] == data['key']]
                    if not history or history[-1]['sha256'] != data['supersedes']:
                        raise JournalIntegrityError('supersession precondition changed; reconcile first')
                if kind == 'revolution_receipt':
                    previous = [e for e in current if e['kind'] == 'revolution_receipt']
                    expected = previous[-1]['data']['receipt']['receipt_sha256'] if previous else ''
                    provided = data['receipt']['previous_receipt_sha256']
                    if provided != expected or data['receipt']['revolution'] != len(previous) + 1:
                        raise JournalIntegrityError('revolution chain does not extend current head')
                event = {
                    'seq': len(current) + 1, 'kind': kind, 'data': deepcopy(data),
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'previous_sha256': current[-1]['sha256'] if current else '',
                }
                event['sha256'] = _digest(event)
                if self.integrity_key is not None:
                    event['auth_tag'] = hmac.new(self.integrity_key, _encoded(event), hashlib.sha256).hexdigest()
                handle.seek(0, os.SEEK_END)
                handle.write(_encoded(event).decode('utf-8') + '\n')
                handle.flush()
                os.fsync(handle.fileno())
                self._events = current + [event]
                return event
            finally:
                if fcntl is not None:
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    @property
    def events(self) -> tuple[dict[str, Any], ...]:
        return tuple(deepcopy(self._events))

    def _matching(self, kind: str, key: str | None = None) -> list[dict[str, Any]]:
        return [e for e in self._events if e['kind'] == kind and
                (key is None or e['data'].get('key', e['data'].get('task_id')) == key)]

    def fact_history(self, key: str) -> list[dict[str, Any]]:
        return deepcopy(self._matching('verified_fact', key) + self._matching('superseded_fact', key))

    def fact(self, key: str) -> dict[str, Any] | None:
        history = sorted(self.fact_history(key), key=lambda x: x['seq'])
        return deepcopy(history[-1]['data']) if history else None

    def verify_fact(self, key: str, value: Any, *, source: str, revision: str = '') -> None:
        if not key.strip() or not source.strip():
            raise ValueError('fact and source reference required')
        prior = self.fact(key)
        if prior:
            if prior['value'] != value:
                raise ValueError('verified facts require explicit supersession')
            return
        self._append('verified_fact', key=key, value=value, source=source, revision=revision)

    def supersede_fact(self, key: str, value: Any, *, source: str, revision: str = '') -> None:
        prior = self.fact_history(key)
        if not prior or not source.strip():
            raise ValueError('prior verified fact and new source required')
        old = max(prior, key=lambda x: x['seq'])
        self._append('superseded_fact', key=key, value=value, source=source,
                     revision=revision, supersedes=old['sha256'])

    def note_conflict(self, key: str, alternative: Any, *, source: str) -> None:
        if not source:
            raise ValueError('conflict source required')
        self._append('fact_conflict', key=key, alternative=alternative, source=source)

    def conflicts(self, key: str) -> list[dict[str, Any]]:
        return deepcopy([e['data'] for e in self._matching('fact_conflict', key)])

    def correct(self, instruction: str) -> None:
        if not instruction.strip():
            raise ValueError('correction required')
        if instruction not in self.corrections:
            self._append('correction', instruction=instruction)

    @property
    def corrections(self) -> list[str]:
        return [e['data']['instruction'] for e in self._matching('correction')]

    def define_task(self, task_id: str, title: str, parent: str | None = None) -> None:
        if not task_id.strip() or not title.strip():
            raise ValueError('task ID and title required')
        if not any(e['data'].get('task_id') == task_id for e in self._matching('task_defined')):
            self._append('task_defined', task_id=task_id, title=title, parent=parent)

    def complete_task(self, task_id: str, receipt: str) -> None:
        if not receipt.strip() or not any(e['data'].get('task_id') == task_id for e in self._matching('task_defined')):
            raise ValueError('defined task and completion receipt required')
        if not self.task_is_complete(task_id):
            self._append('task_completed', task_id=task_id, receipt=receipt)

    def task_is_complete(self, task_id: str) -> bool:
        return bool(self._matching('task_completed', task_id))

    def checkpoint(self, cursor: str, *, detail: str = '') -> None:
        if not cursor:
            raise ValueError('resume cursor required')
        self._append('checkpoint', cursor=cursor, detail=detail)

    @property
    def cursor(self) -> str:
        history = self._matching('checkpoint')
        return history[-1]['data']['cursor'] if history else ''

    def route_attempted(self, route: str) -> bool:
        return any(e['kind'] in {'route_started', 'route_succeeded', 'route_failed'} and
                   e['data']['route'] == route for e in self._events)

    def route_succeeded(self, route: str) -> bool:
        return any(e['data']['route'] == route for e in self._matching('route_succeeded'))

    @property
    def revolution_receipts(self):
        from .revolution_controller import RevolutionReceipt, verify_receipt_chain
        values = tuple(RevolutionReceipt(**deepcopy(e['data']['receipt']))
                       for e in self._matching('revolution_receipt'))
        valid, reason = verify_receipt_chain(values)
        if not valid:
            raise JournalIntegrityError(f'invalid persisted revolution proof: {reason}')
        return values

    def append_revolution(self, receipt) -> None:
        from .revolution_controller import RevolutionReceipt
        if not isinstance(receipt, RevolutionReceipt) or not receipt.verify():
            raise ValueError('a verified revolution receipt is required')
        self._append('revolution_receipt', receipt=asdict(receipt))

    @property
    def improvement_history(self):
        """Recover proven or disputed improvement assessments across sessions."""
        from .improvement import ImprovementAssessment
        values = tuple(ImprovementAssessment(**deepcopy(e['data']['assessment']))
                       for e in self._matching('improvement_assessment'))
        if not all(value.verify() for value in values):
            raise JournalIntegrityError('invalid improvement assessment proof')
        return values

    def record_improvement(self, assessment) -> None:
        """Append an assessment without conflating it with mission completion."""
        from .improvement import ImprovementAssessment
        if not isinstance(assessment, ImprovementAssessment) or not assessment.verify():
            raise ValueError('verified improvement assessment structure required')
        if (assessment.mission_id, assessment.objective, assessment.terminal_outcome) != (
                self.mission_id, self.objective, self.terminal_outcome):
            raise ValueError('improvement assessment belongs to a different mission')
        self._append('improvement_assessment', assessment=asdict(assessment))

    @property
    def is_complete(self) -> bool:
        return bool(self._matching('mission_complete'))

    def complete(self, provider_receipt: str, *, outcome_type: str,
                 verifier: Callable[[OutcomeEvidence], bool] | None = None) -> None:
        if not isinstance(provider_receipt, str) or not provider_receipt.strip() or outcome_type != self.terminal_outcome:
            raise ValueError('outcome type must match assigned mission and carry source-native receipt')
        evidence = OutcomeEvidence(outcome_type, provider_receipt)
        if verifier is None or not verifier(evidence):
            raise ValueError('independent terminal outcome verification required')
        if not self.is_complete:
            self._append('mission_complete', provider_receipt=provider_receipt, outcome_type=outcome_type)


@dataclass(frozen=True)
class RouteResult:
    success: bool
    detail: str = ''
    receipt: str = ''


@dataclass(frozen=True)
class OutcomeEvidence:
    outcome_type: str
    receipt: str


@dataclass(frozen=True)
class MissionRunResult:
    state: str
    attempted: tuple[str, ...]
    cursor: str


class MissionRunner:
    """Execute alternate routes and stop only after provider-backed outcome proof.

    A route identifier denotes one concrete attempt, not a permanent capability ban.
    To retry an altered route, issue a new attempt identifier. A finite run
    budget makes work resumable; it never converts friction into terminal failure.
    """

    def __init__(self, journal: ContinuityJournal):
        self.journal = journal

    def run(self, routes: Iterable[str], perform: Callable[[str], RouteResult],
            outcome_evidence: Callable[[ContinuityJournal], OutcomeEvidence | None],
            *, max_attempts: int = 20,
            verify_outcome: Callable[[OutcomeEvidence], bool] | None = None) -> MissionRunResult:
        if max_attempts < 1:
            raise ValueError('max_attempts must be positive')
        if self.journal.is_complete:
            return MissionRunResult('COMPLETE', (), self.journal.cursor)
        attempted: list[str] = []
        def matches_terminal(evidence: OutcomeEvidence | None) -> bool:
            return bool(isinstance(evidence, OutcomeEvidence) and
                        evidence.outcome_type == self.journal.terminal_outcome and
                        evidence.receipt.strip() and verify_outcome is not None
                        and verify_outcome(evidence))

        known = outcome_evidence(self.journal)
        if matches_terminal(known):
            self.journal.complete(known.receipt, outcome_type=known.outcome_type,
                                  verifier=verify_outcome)
            return MissionRunResult('COMPLETE', (), self.journal.cursor)
        # Finite scan budget also bounds infinite streams of already-attempted routes.
        from itertools import islice
        for route in islice(routes, max_attempts * 10):
            if len(attempted) >= max_attempts:
                break
            if self.journal.route_attempted(route):
                continue
            # Persist the attempt BEFORE touching an external provider. On crash,
            # reconciliation must establish the external result before any replay.
            self.journal._append('route_started', route=route,
                                 idempotency_key=_digest({'mission': self.journal.mission_id,
                                                          'route': route}))
            result = perform(route)
            if not isinstance(result, RouteResult):
                raise TypeError('perform must return RouteResult')
            attempted.append(route)
            kind = 'route_succeeded' if result.success and result.receipt.strip() else 'route_failed'
            self.journal._append(kind, route=route, detail=result.detail,
                                 receipt=result.receipt)
            evidence = outcome_evidence(self.journal)
            if matches_terminal(evidence):
                self.journal.complete(evidence.receipt, outcome_type=evidence.outcome_type,
                                      verifier=verify_outcome)
                return MissionRunResult('COMPLETE', tuple(attempted), self.journal.cursor)
        self.journal.checkpoint('route-discovery', detail='Mission open; renew route plan from latest verified state')
        return MissionRunResult('RESUMABLE', tuple(attempted), self.journal.cursor)