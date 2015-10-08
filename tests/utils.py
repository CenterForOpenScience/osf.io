import mock
import contextlib
import functools
from nose import SkipTest
from nose.tools import assert_equal, assert_not_equal
from django.http import HttpRequest

from framework.auth import Auth

from website.archiver import listeners as archiver_listeners
from website.archiver import ARCHIVER_SUCCESS

def requires_module(module):
    def decorator(fn):
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            try:
                __import__(module)
            except ImportError:
                raise SkipTest()
            return fn(*args, **kwargs)
        return wrapper
    return decorator


def assert_logs(log_action, node_key, index=-1):
    """A decorator to ensure a log is added during a unit test.
    :param str log_action: NodeLog action
    :param str node_key: key to get Node instance from self
    :param int index: list index of log to check against

    Example usage:
    @assert_logs(NodeLog.UPDATED_FIELDS, 'node')
    def test_update_node(self):
        self.node.update({'title': 'New Title'}, auth=self.auth)

    TODO: extend this decorator to check log param correctness?
    """
    def outer_wrapper(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            node = getattr(self, node_key)
            last_log = node.logs[-1]
            func(self, *args, **kwargs)
            node.reload()
            new_log = node.logs[index]
            assert_not_equal(last_log._id, new_log._id)
            assert_equal(new_log.action, log_action)
            node.save()
        return wrapper
    return outer_wrapper

def assert_not_logs(log_action, node_key, index=-1):
    def outer_wrapper(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            node = getattr(self, node_key)
            last_log = node.logs[-1]
            func(self, *args, **kwargs)
            node.reload()
            new_log = node.logs[index]
            assert_not_equal(new_log.action, log_action)
            assert_equal(last_log._id, new_log._id)
            node.save()
        return wrapper
    return outer_wrapper

@contextlib.contextmanager
def mock_archive(project, schema=None, auth=None, template=None, data=None, parent=None,
                 autocomplete=True, autoapprove=False):
    """ A context manager for registrations. When you want to call Node#register_node in
    a test but do not want to deal with any of this side effects of archiver, this
    helper allows for creating a registration in a safe fashion.

    :param bool autocomplete: automatically finish archival?
    :param bool autoapprove: automatically approve registration approval?

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
    schema = schema or None
    auth = auth or Auth(project.creator)
    template = template or ''
    data = data or ''

    with mock.patch('framework.tasks.handlers.enqueue_task'):
        registration = project.register_node(schema, auth, template, data, parent)
    registration.root.require_approval(project.creator)
    if autocomplete:
        root_job = registration.root.archive_job
        root_job.status = ARCHIVER_SUCCESS
        root_job.sent = False
        root_job.done = True
        root_job.save()
        sanction = registration.root.sanction
        with contextlib.nested(
            mock.patch.object(root_job, 'archive_tree_finished', mock.Mock(return_value=True)),
            mock.patch.object(sanction, 'ask')
        ):
            archiver_listeners.archive_callback(registration)
    if autoapprove:
        sanction = registration.root.sanction
        sanction._on_complete(project.creator)
    yield registration

def make_drf_request(*args, **kwargs):
    from rest_framework.request import Request
    http_request = HttpRequest()
    # The values here don't matter; they just need
    # to be present
    http_request.META['SERVER_NAME'] = 'localhost'
    http_request.META['SERVER_PORT'] = 8000
    # A DRF Request wraps a Django HttpRequest
    return Request(http_request, *args, **kwargs)
