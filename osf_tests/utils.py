import contextlib
import datetime as dt
import functools
import mock

from modularodm.storage import EphemeralStorage
from framework.auth import Auth
from django.utils import timezone

import blinker
from website.signals import ALL_SIGNALS
from website.archiver import ARCHIVER_SUCCESS
from website.archiver import listeners as archiver_listeners

from osf.models import Sanction

from .factories import get_default_metaschema


def set_up_ephemeral_storage(schemas):
    for schema in schemas:
        schema.set_storage(EphemeralStorage(collection_name=schema._name))


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

@contextlib.contextmanager
def mock_archive(project, schema=None, auth=None, data=None, parent=None,
                 embargo=False, embargo_end_date=None,
                 retraction=False, justification=None, autoapprove_retraction=False,
                 autocomplete=True, autoapprove=False):
    """ A context manager for registrations. When you want to call Node#register_node in
    a test but do not want to deal with any of this side effects of archiver, this
    helper allows for creating a registration in a safe fashion.

    :param bool embargo: embargo the registration (rather than RegistrationApproval)
    :param bool autocomplete: automatically finish archival?
    :param bool autoapprove: automatically approve registration approval?
    :param bool retraction: retract the registration?
    :param str justification: a justification for the retraction
    :param bool autoapprove_retraction: automatically approve retraction?

    Example use:

    project = ProjectFactory()
    with mock_archive(project) as registration:
        assert_true(registration.is_registration)
        assert_true(registration.archiving)
        assert_true(registration.is_pending_registration)

    with mock_archive(project, autocomplete=True) as registration:
        assert_true(registration.is_registration)
        assert_false(registration.archiving)
        assert_true(registration.is_pending_registration)

    with mock_archive(project, autocomplete=True, autoapprove=True) as registration:
        assert_true(registration.is_registration)
        assert_false(registration.archiving)
        assert_false(registration.is_pending_registration)
    """
    schema = schema or get_default_metaschema()
    auth = auth or Auth(project.creator)
    data = data or ''

    with mock.patch('framework.celery_tasks.handlers.enqueue_task'):
        registration = project.register_node(
            schema=schema,
            auth=auth,
            data=data,
            parent=parent,
        )
    if embargo:
        embargo_end_date = embargo_end_date or (
            timezone.now() + dt.timedelta(days=20)
        )
        registration.embargo_registration(
            project.creator,
            embargo_end_date
        )
    else:
        registration.require_approval(project.creator)
    if autocomplete:
        root_job = registration.archive_job
        root_job.status = ARCHIVER_SUCCESS
        root_job.sent = False
        root_job.done = True
        root_job.save()
        sanction = registration.sanction
        with contextlib.nested(
            mock.patch.object(root_job, 'archive_tree_finished', mock.Mock(return_value=True)),
            mock.patch('website.archiver.tasks.archive_success.delay', mock.Mock())
        ):
            archiver_listeners.archive_callback(registration)
    if autoapprove:
        sanction = registration.sanction
        sanction.state = Sanction.APPROVED
        sanction.save()
        sanction._on_complete(project.creator)
        sanction.save()

    if retraction:
        justification = justification or 'Because reasons'
        registration.refresh_from_db()
        retraction = registration.retract_registration(project.creator, justification=justification)
        if autoapprove_retraction:
            retraction.state = Sanction.APPROVED
            retraction._on_complete(project.creator)
        retraction.save()
        registration.save()
    yield registration
