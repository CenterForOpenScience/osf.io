import contextlib
import datetime
import functools
import mock

from django.http import HttpRequest
from django.utils import timezone
from nose import SkipTest
from nose.tools import assert_equal, assert_not_equal

from framework.auth import Auth
from framework.celery_tasks.handlers import celery_teardown_request
from framework.postcommit_tasks.handlers import postcommit_after_request
from osf.models import Sanction
from tests.base import get_default_metaschema
from website.archiver import ARCHIVER_SUCCESS
from website.archiver import listeners as archiver_listeners

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
            last_log = node.logs.latest()
            func(self, *args, **kwargs)
            node.reload()
            new_log = node.logs.order_by('-date')[-index - 1]
            assert_not_equal(last_log._id, new_log._id)
            assert_equal(new_log.action, log_action)
            node.save()
        return wrapper
    return outer_wrapper

def assert_preprint_logs(log_action, preprint_key, index=-1):
    """A decorator to ensure a log is added during a unit test.
    :param str log_action: PreprintLog action
    :param str preprint_key: key to get Preprint instance from self
    :param int index: list index of log to check against

    Example usage:
    @assert_logs(PreprintLog.UPDATED_FIELDS, 'preprint')
    def test_update_preprint(self):
        self.preprint.update({'title': 'New Title'}, auth=self.auth)

    TODO: extend this decorator to check log param correctness?
    """
    def outer_wrapper(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            preprint = getattr(self, preprint_key)
            last_log = preprint.logs.latest()
            func(self, *args, **kwargs)
            preprint.reload()
            new_log = preprint.logs.order_by('-created')[-index - 1]
            assert_not_equal(last_log._id, new_log._id)
            assert_equal(new_log.action, log_action)
            preprint.save()
        return wrapper
    return outer_wrapper

def assert_not_logs(log_action, node_key, index=-1):
    def outer_wrapper(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            node = getattr(self, node_key)
            last_log = node.logs.latest()
            func(self, *args, **kwargs)
            node.reload()
            new_log = node.logs.order_by('-date')[-index - 1]
            assert_not_equal(new_log.action, log_action)
            assert_equal(last_log._id, new_log._id)
            node.save()
        return wrapper
    return outer_wrapper

def assert_items_equal(item_one, item_two):
    item_one.sort()
    item_two.sort()
    assert item_one == item_two

@contextlib.contextmanager
def assert_latest_log(log_action, node_key, index=0):
    node = node_key
    last_log = node.logs.latest()
    node.reload()
    yield
    new_log = node.logs.order_by('-date')[index] if hasattr(last_log, 'date') else node.logs.order_by('-created')[index]
    assert last_log._id != new_log._id
    assert new_log.action == log_action

@contextlib.contextmanager
def assert_latest_log_not(log_action, node_key, index=0):
    node = node_key
    last_log = node.logs.latest()
    node.reload()
    yield
    new_log = node.logs.order_by('-date')[index] if hasattr(last_log, 'date') else node.logs.order_by('-created')[index]
    assert new_log.action != log_action
    assert last_log._id == new_log._id

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
            timezone.now() + datetime.timedelta(days=20)
        )
        registration.root.embargo_registration(
            project.creator,
            embargo_end_date
        )
    else:
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
            mock.patch('website.archiver.tasks.archive_success.delay', mock.Mock())
        ):
            archiver_listeners.archive_callback(registration)
    if autoapprove:
        sanction = registration.root.sanction
        sanction.state = Sanction.APPROVED
        # save or _on_complete no worky
        sanction.save()
        sanction._on_complete(project.creator)
        sanction.save()

    if retraction:
        justification = justification or 'Because reasons'
        retraction = registration.retract_registration(project.creator, justification=justification)
        if autoapprove_retraction:
            retraction.state = Sanction.APPROVED
            retraction._on_complete(project.creator)
        retraction.save()
        registration.save()
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

def make_drf_request_with_version(version='2.0', *args, **kwargs):
    req = make_drf_request(*args, **kwargs)
    req.parser_context['kwargs'] = {'version': 'v2'}
    req.version = version
    return req

class MockAuth(object):

    def __init__(self, user):
        self.user = user
        self.logged_in = True
        self.private_key = None
        self.private_link = None

mock_auth = lambda user: mock.patch('framework.auth.Auth.from_kwargs', mock.Mock(return_value=MockAuth(user)))

def unique(factory):
    """
    Turns a factory function into a new factory function that guarentees unique return
    values. Note this uses regular item equivalence to check uniqueness, so this may not
    behave as expected with factories with complex return values.

    Example use:
    unique_name_factory = unique(fake.name)
    unique_name = unique_name_factory()
    """
    used = []
    @functools.wraps(factory)
    def wrapper():
        item = factory()
        over = 0
        while item in used:
            if over > 100:
                raise RuntimeError('Tried 100 times to generate a unqiue value, stopping.')
            item = factory()
            over += 1
        used.append(item)
        return item
    return wrapper

@contextlib.contextmanager
def run_celery_tasks():
    yield
    celery_teardown_request()
