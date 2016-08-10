import datetime as dt
import functools

import blinker
from website.signals import ALL_SIGNALS

# From Flask-Security: https://github.com/mattupstate/flask-security/blob/develop/flask_security/utils.py
class CaptureSignals(object):
    """Testing utility for capturing blinker signals.

    Context manager which mocks out selected signals and registers which
    are `sent` on and what arguments were sent. Instantiate with a list of
    blinker `NamedSignals` to patch. Each signal has its `send` mocked out.

    """
    def __init__(self, signals):
        """Patch all given signals and make them available as attributes.

        :param signals: list of signals

        """
        self._records = {}
        self._receivers = {}
        for signal in signals:
            self._records[signal] = []
            self._receivers[signal] = functools.partial(self._record, signal)

    def __getitem__(self, signal):
        """All captured signals are available via `ctxt[signal]`.
        """
        if isinstance(signal, blinker.base.NamedSignal):
            return self._records[signal]
        else:
            super(CaptureSignals, self).__setitem__(signal)

    def _record(self, signal, *args, **kwargs):
        self._records[signal].append((args, kwargs))

    def __enter__(self):
        for signal, receiver in self._receivers.items():
            signal.connect(receiver)
        return self

    def __exit__(self, type, value, traceback):
        for signal, receiver in self._receivers.items():
            signal.disconnect(receiver)

    def signals_sent(self):
        """Return a set of the signals sent.
        :rtype: list of blinker `NamedSignals`.

        """
        return set([signal for signal, _ in self._records.items() if self._records[signal]])


def capture_signals():
    """Factory method that creates a ``CaptureSignals`` with all OSF signals."""
    return CaptureSignals(ALL_SIGNALS)

def assert_datetime_equal(dt1, dt2, allowance=500):
    """Assert that two datetimes are about equal."""

    assert abs(dt1 - dt2) < dt.timedelta(milliseconds=allowance)
