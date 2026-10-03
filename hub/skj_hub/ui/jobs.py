"""Run hub calls off the UI thread (spec §4.3).

Queries (search, lists) run in parallel. Anything that changes the system
runs one at a time, in order, on its own queue. Results come back on the UI
thread through Qt signals.
"""

from __future__ import annotations

import logging
from threading import Event

from PySide6.QtCore import QObject, QRunnable, QThreadPool, Signal

log = logging.getLogger(__name__)


class _Signals(QObject):
    progress = Signal(object, str)  # percent or None, status
    done = Signal(object)  # return value
    failed = Signal(str)


class Job(QRunnable):
    def __init__(self, fn, *, with_progress: bool = False):
        super().__init__()
        self.fn = fn
        self.with_progress = with_progress
        self.cancel = Event()
        self.signals = _Signals()
        # Jobs keeps the reference until the result is delivered: an
        # auto-deleted runnable would free its signals with a result in flight.
        self.setAutoDelete(False)

    def run(self):
        try:
            if self.with_progress:
                value = self.fn(
                    lambda pct, status: self.signals.progress.emit(pct, status), self.cancel
                )
            else:
                value = self.fn()
            self.signals.done.emit(value)
        except Exception as e:  # backends shouldn't raise; this is the last net
            log.exception("job failed")
            self.signals.failed.emit(str(e))


class Jobs(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.queries = QThreadPool(self)
        self.queries.setMaxThreadCount(4)
        self.changes = QThreadPool(self)
        self.changes.setMaxThreadCount(1)  # one system change at a time
        self._running: set[Job] = set()

    def _start(self, pool: QThreadPool, job: Job, on_done, on_failed) -> Job:
        self._running.add(job)
        job.signals.done.connect(on_done)
        if on_failed:
            job.signals.failed.connect(on_failed)
        job.signals.done.connect(lambda _v, j=job: self._running.discard(j))
        job.signals.failed.connect(lambda _e, j=job: self._running.discard(j))
        pool.start(job)
        return job

    def query(self, fn, on_done, on_failed=None) -> Job:
        return self._start(self.queries, Job(fn), on_done, on_failed)

    def change(self, fn, on_progress, on_done, on_failed=None) -> Job:
        job = Job(fn, with_progress=True)
        job.signals.progress.connect(on_progress)
        return self._start(self.changes, job, on_done, on_failed)

    def wait(self, msecs: int = 30000) -> bool:
        return self.queries.waitForDone(msecs) and self.changes.waitForDone(msecs)
