from datetime import datetime, timedelta, timezone

from aqt import mw
from aqt.qt import QTimer

from .config import config
from .utils import query_op


class Timers:
    def __init__(self):
        self.submit_reviews_timer = QTimer(mw)
        self.submit_reviews_timer.setSingleShot(True)
        self.submit_reviews_timer.timeout.connect(self.submit_reviews_timeout)

        self.submit_lessons_timer = QTimer(mw)
        self.submit_lessons_timer.timeout.connect(self.submit_lessons_timeout)

        self.sync_due_timer = QTimer(mw)
        self.sync_due_timer.timeout.connect(self.sync_due_timeout)

    def start_timers(self):
        delta = timedelta(**config.SYNC_INTERVAL_LESSONS)
        self.submit_lessons_timer.start(int(delta.total_seconds() * 1000))

        delta = timedelta(**config.SYNC_INTERVAL_DUE)
        self.sync_due_timer.start(int(delta.total_seconds() * 1000))

        self.start_reviews_timer()

    def submit_reviews_at(self, time: datetime):
        now = datetime.now(timezone.utc)
        remaining = self.submit_reviews_timer.remainingTime()
        if remaining < 0 or time < now + timedelta(milliseconds=remaining):
            self.submit_reviews_timer.start(int((time - now).total_seconds() * 1000))

    @query_op
    def start_reviews_timer(self):
        from .sync import SyncOp
        time = SyncOp().get_next_assignment_available()
        mw.taskman.run_on_main(lambda: self.submit_reviews_at(time))

    def submit_reviews_timeout(self):
        from .sync import SyncOp
        SyncOp().upstream_available_assignments(reviews=True, lessons=False)
        self.start_reviews_timer()

    def sync_due_timeout(self):
        from .sync import SyncOp

        SyncOp().update_intervals()

    def submit_lessons_timeout(self):
        from .sync import SyncOp
        SyncOp().upstream_available_assignments(reviews=False, lessons=True)


timers = Timers()
