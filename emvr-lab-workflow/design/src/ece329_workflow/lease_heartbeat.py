"""Renew job ownership while waiting for a provider; crashes still expire."""
import logging
from threading import Event, Thread


class LeaseHeartbeat:
    def __init__(self, renew, interval=60):
        self.renew, self.interval = renew, interval
        self.stop = Event()
        self.thread = None

    def __enter__(self):
        def run():
            while not self.stop.wait(self.interval):
                try:
                    if not self.renew():
                        return
                except Exception as exc:
                    logging.getLogger(__name__).error('Job lease renewal failed type=%s', type(exc).__name__)
        self.thread = Thread(target=run, daemon=True, name='model-job-lease')
        self.thread.start()
        return self

    def __exit__(self, *args):
        self.stop.set()
        self.thread.join(timeout=2)
