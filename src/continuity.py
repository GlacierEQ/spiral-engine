"""Spiral Engine continuity: verified-state inheritance, alternate routes, durable outcome gates.

An authenticated source receipt establishes a fact until a later source-backed
supersession. Route friction never completes or permanently blocks a mission.
A quality score or a successful intermediate artifact never completes a mission.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
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


def _load(raw: str) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    previous = ''
    for index, line in enumerate(raw.splitlines(), 1):
        try:
            event = json.loads(line)
            provided = event.pop('sha256')
            if (event['seq'] != index or event['previous_sha256'] != previous
                    or provided != _digest(event)):
                raise JournalIntegrityError(f'broken event chain at {index}')
            event['sha256'] = provided
        except (KeyError, TypeError, ValueError) as exc:
            raise JournalIntegrityError(f'invalid event at {index}') from exc
        events.append(event)
        previous = provided
    return events


class ContinuityJournal:
    """Append-only, SHA-linked mission journal with explicit source authority."""

    def __init__(self, path: Path | str, mission_id: str, objective: str):
        if not mission_id.strip() or not objective.strip():
            raise ValueError('mission identity and objective required')
        self.path = Path(path)
        self.mission_id = mission_id
        self.objective = objective
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._events = _load(self.path.read_text('utf-8')) if self.path.exists() else []
        if self._events:
            first = self._events[0]
            if (first['kind'] != 'mission' or first['data'] !=
                    {'mission_id': mission_id, 'objective': objective}):
                raise JournalIntegrityError('mission identity mismatch')
        else:
            self._append('mission', mission_id=mission_id, objective=objective)

    def _append(self, kind: str, **data: Any) -> dict[str, Any]:
        with self.path.open('a+', encoding='utf-8') as handle:
            if fcntl is not None:
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            try:
                handle.seek(0)
                current = _load(handle.read())
                if current and self._events and current[0]['sha256'] != self._events[0]['sha256']:
                    raise JournalIntegrityError('mission journal changed')
                event = {
                    'seq': len(current) + 1, 'kind': kind, 'data': data,
                    'timestamp': datetime.now(timezone.utc).isoformat(),
                    'previous_sha256': current[-1]['sha256'] if current else '',
                }
                event['sha256'] = _digest(event)
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
        return tuple(self._events)

    def _matching(self, kind: str, key: str | None = None) -> list[dict[str, Any]]:
        return [e for e in self._events if e['kind'] == kind and
                (key is None or e['data'].get('key', e['data'].get('task_id')) == key)]

    def fact_history(self, key: str) -> list[dict[str, Any]]:
        return self._matching('verified_fact', key) + self._matching('superseded_fact', key)

    def fact(self, key: str) -> dict[str, Any] | None:
        history = sorted(self.fact_history(key), key=lambda x: x['seq'])
        return history[-1]['data'] if history else None

    def verify_fact(self, key: str, value: Any, *, source: str, revision: str = '') -> None:
        if not key or not source:
            raise ValueError('fact and source reference required')
        prior = self.fact(key)
        if prior:
            if prior['value'] != value:
                raise ValueError('verified facts require explicit supersession')
            return
        self._append('verified_fact', key=key, value=value, source=source, revision=revision)

    def supersede_fact(self, key: str, value: Any, *, source: str, revision: str = '') -> None:
        prior = self.fact_history(key)
        if not prior or not source:
            raise ValueError('prior verified fact and new source required')
        old = max(prior, key=lambda x: x['seq'])
        self._append('superseded_fact', key=key, value=value, source=source,
                     revision=revision, supersedes=old['sha256'])

    def note_conflict(self, key: str, alternative: Any, *, source: str) -> None:
        if not source:
            raise ValueError('conflict source required')
        self._append('fact_conflict', key=key, alternative=alternative, source=source)

    def conflicts(self, key: str) -> list[dict[str, Any]]:
        return [e['data'] for e in self._matching('fact_conflict', key)]

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
        if not receipt or not any(e['data'].get('task_id') == task_id for e in self._matching('task_defined')):
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
        return any(e['kind'] in {'route_succeeded', 'route_failed'} and
                   e['data']['route'] == route for e in self._events)

    def route_succeeded(self, route: str) -> bool:
        return any(e['data']['route'] == route for e in self._matching('route_succeeded'))

    @property
    def is_complete(self) -> bool:
        return bool(self._matching('mission_complete'))

    def complete(self, provider_receipt: str) -> None:
        if not provider_receipt:
            raise ValueError('outcome must have source-native receipt')
        if not self.is_complete:
            self._append('mission_complete', provider_receipt=provider_receipt)


@dataclass(frozen=True)
class RouteResult:
    success: bool
    detail: str = ''
    receipt: str = ''


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
            outcome_evidence: Callable[[ContinuityJournal], str | None],
            *, max_attempts: int = 20) -> MissionRunResult:
        if max_attempts < 1:
            raise ValueError('max_attempts must be positive')
        if self.journal.is_complete:
            return MissionRunResult('COMPLETE', (), self.journal.cursor)
        attempted: list[str] = []
        known = outcome_evidence(self.journal)
        if known:
            self.journal.complete(known)
            return MissionRunResult('COMPLETE', (), self.journal.cursor)
        for route in routes:
            if len(attempted) >= max_attempts:
                break
            if self.journal.route_attempted(route):
                continue
            result = perform(route)
            if not isinstance(result, RouteResult):
                raise TypeError('perform must return RouteResult')
            attempted.append(route)
            kind = 'route_succeeded' if result.success and result.receipt else 'route_failed'
            self.journal._append(kind, route=route, detail=result.detail,
                                 receipt=result.receipt)
            evidence = outcome_evidence(self.journal)
            if evidence:
                self.journal.complete(evidence)
                return MissionRunResult('COMPLETE', tuple(attempted), self.journal.cursor)
        self.journal.checkpoint('route-discovery', detail='Mission open; renew route plan from latest verified state')
        return MissionRunResult('RESUMABLE', tuple(attempted), self.journal.cursor)