from collections import Counter
import datetime
import functools
from unittest import mock
import requests
import waffle

from django.apps import apps
from django.http import HttpRequest
from django.utils import timezone
import contextlib
from typing import Any, Optional

from framework.auth import Auth
from framework.celery_tasks.handlers import celery_teardown_request
from osf.email import _render_email_html
from osf_tests.factories import DraftRegistrationFactory
from osf.models import Sanction, NotificationType
from tests.base import get_default_metaschema
from website.archiver import ARCHIVER_SUCCESS
from website.archiver import listeners as archiver_listeners
from website import settings as website_settings
from osf import features

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
            assert last_log._id != new_log._id
            assert new_log.action == log_action
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
            assert last_log._id != new_log._id
            assert new_log.action == log_action
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
            assert new_log.action != log_action
            assert last_log._id == new_log._id
            node.save()
        return wrapper
    return outer_wrapper

def assert_equals(item_one, item_two):
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
def mock_archive(project, schema=None, auth=None, draft_registration=None, parent=None,
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
    draft_registration = draft_registration or DraftRegistrationFactory(branched_from=project, registration_schema=schema)

    with mock.patch('framework.celery_tasks.handlers.enqueue_task'):
        registration = draft_registration.register(auth=auth, save=True)

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
        mock.patch.object(root_job, 'archive_tree_finished', mock.Mock(return_value=True))
        mock.patch('website.archiver.tasks.archive_success.delay', mock.Mock())
        archiver_listeners.archive_callback(registration)

    if autoapprove:
        sanction = registration.root.sanction
        sanction.accept()

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

class MockAuth:

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


@contextlib.contextmanager
def capture_notifications(capture_email: bool = True, passthrough: bool = False):
    """
    Capture NotificationType emits (including calls via NotificationType.Type.<X>.instance.emit)
    and optionally capture email sends.

    Asserts (post-yield):
      - At least one notification was emitted.
      - Every captured email successfully renders via _render_email_html.

    Returns:
        dict: {
            "emits":  [ {"type": str, "args": tuple, "kwargs": dict}, ... ],
            "emails": [ {"protocol": str, "to": ..., "notification_type": ..., "context": ..., "email_context": ...}, ... ]
        }
    """
    from osf.email import _render_email_html
    try:
        from osf.email import _extract_vars as _extract_template_vars
    except Exception:
        _extract_template_vars = None

    NotificationTypeModel = apps.get_model('osf', 'NotificationType')
    captured = {'emits': [], 'emails': []}

    # Patch the instance method so ALL emit paths are captured
    _real_emit = NotificationTypeModel.emit

    def _wrapped_emit(self, *emit_args, **emit_kwargs):
        captured['emits'].append({
            'type': getattr(self, 'name', None),
            'args': emit_args,
            'kwargs': emit_kwargs,
        })
        if passthrough:
            return _real_emit(self, *emit_args, **emit_kwargs)

    patches = [
        mock.patch('osf.models.notification_type.NotificationType.emit', new=_wrapped_emit),
    ]

    if capture_email:
        from osf import email as _osf_email
        _real_send_over_smtp = _osf_email.send_email_over_smtp
        _real_send_with_sendgrid = _osf_email.send_email_with_send_grid

        def _fake_send_over_smtp(to_email, notification_type, context=None, email_context=None):
            captured['emails'].append({
                'protocol': 'smtp',
                'to': to_email,
                'notification_type': notification_type,
                'context': context.copy() if isinstance(context, dict) else context,
                'email_context': email_context.copy() if isinstance(email_context, dict) else email_context,
            })
            if passthrough:
                return _real_send_over_smtp(to_email, notification_type, context, email_context)

        def _fake_send_with_sendgrid(user, notification_type, context=None, email_context=None):
            captured['emails'].append({
                'protocol': 'sendgrid',
                'to': user,
                'notification_type': notification_type,
                'context': context.copy() if isinstance(context, dict) else context,
                'email_context': email_context.copy() if isinstance(email_context, dict) else email_context,
            })
            if passthrough:
                return _real_send_with_sendgrid(user, notification_type, context, email_context)

        patches.extend([
            mock.patch('osf.email.send_email_over_smtp', new=_fake_send_over_smtp),
            mock.patch('osf.email.send_email_with_send_grid', new=_fake_send_with_sendgrid),
        ])

    with contextlib.ExitStack() as stack:
        for p in patches:
            stack.enter_context(p)
        yield captured

    if not captured['emits']:
        raise AssertionError(
            'No notifications were emitted. '
            'Expected at least one call to NotificationType.emit. '
            'Tip: ensure your code path triggers an emit and that patches did not get overridden.'
        )

    for idx, rec in enumerate(captured.get('emits', []), start=1):
        nt = NotificationType.objects.get(name=rec.get('type'))
        name = getattr(nt, 'name', '(unknown)')
        template_text = getattr(nt, 'template', '') or ''
        rendered = _render_email_html(nt, rec['kwargs']['event_context'])
        # Fail if rendering produced nothing
        if not isinstance(rendered, str) or not rendered.strip():
            missing = set()
            if _extract_template_vars:
                try:
                    missing = set(_extract_template_vars(template_text)) - set(ctx.keys())
                except Exception:
                    pass
            hint = f' Likely missing variables: {sorted(missing)}.' if missing else ''
            raise AssertionError(
                f'Email render produced empty/blank HTML for notification "{name}" '
                f'(index {idx}, protocol={rec.get("protocol")}).{hint}'
            )

        # Fail if rendering just echoed the raw template text (Mako likely failed and _render returned template)
        if template_text and rendered.strip() == template_text.strip():
            missing = set()
            if _extract_template_vars:
                try:
                    missing = set(_extract_template_vars(template_text)) - set(rec.keys())
                except Exception:
                    pass
            raise AssertionError(
                f'Email render returned the raw template (no interpolation) for "{name}" '
                f'(index {idx}, protocol={rec.get("protocol")}). '
                f'This usually means Mako failed and _render_email_html fell back to the template.'
                f'{f" Missing variables: {sorted(missing)}." if missing else ""}'
            )



def get_mailhog_messages():
    """Fetch messages from MailHog API."""
    if not waffle.switch_is_active(features.ENABLE_MAILHOG):
        return []
    mailhog_url = f'{website_settings.MAILHOG_API_HOST}/api/v2/messages'
    response = requests.get(mailhog_url)
    if response.status_code == 200:
        return response.json()
    return []


def delete_mailhog_messages():
    """Delete all messages from MailHog."""
    if not waffle.switch_is_active(features.ENABLE_MAILHOG):
        return
    mailhog_url = f'{website_settings.MAILHOG_API_HOST}/api/v1/messages'
    requests.delete(mailhog_url)


def assert_emails(mailhog_messages, notifications):
    expected_html = []
    actual_html = []
    expected_reciver = []
    actual_reciver = []

    normalize = lambda s: s.replace('\r\n', '\n').replace('\r', '\n')

    for item in notifications['emits']:
        expected_reciver.append(item['kwargs']['user'].username)
        expected = _render_email_html(
            NotificationType.objects.get(name=item['type']),
            item['context']
        )

        expected_html.append(normalize(expected).rstrip('\n'))

    for item in mailhog_messages['items']:
        actual_reciver.append(item['Content']['Headers']['To'][0])
        actual = item['Content']['Body']
        actual_html.append(normalize(actual).rstrip('\n'))
    assert Counter(expected_html) == Counter(actual_html)
    assert Counter(expected_reciver) == Counter(actual_reciver)

def _notif_type_name(t: Any) -> str:
    """
    Normalize a NotificationType-ish input to its lowercase name.
    Accepts:
      - NotificationType instance (has .name)
      - NotificationType.Type enum (often stringifiable or has .name)
      - raw string
    """
    if t is None:
        return ''
    # If it's the model instance
    n = getattr(t, 'name', None)
    if n:
        return str(n).strip().lower()
    # If it's an enum-like with .value/.name
    for attr in ('value', 'NAME', 'name'):
        if hasattr(t, attr):
            try:
                return str(getattr(t, attr)).strip().lower()
            except Exception:
                pass
    # Fallback to str()
    return str(t).strip().lower()


def _safe_user_id(u: Any) -> Optional[str]:
    """
    Try to normalize a user object to a stable identifier used in emit kwargs.
    Your emit calls pass the 'user' object itself; we compare object identity if available,
    otherwise fall back to guid/_id if present.
    """
    if u is None:
        return None
    for attr in ('_id', 'id', 'guids', 'guid', 'pk'):
        if hasattr(u, attr):
            try:
                val = getattr(u, attr)
                # guids may be a related manager; try to pull string
                if hasattr(val, 'first'):
                    g = val.first()
                    if g and hasattr(g, '_id'):
                        return g._id
                if isinstance(val, (str, int)):
                    return str(val)
            except Exception:
                pass
    # Last resort: object id
    return f'obj:{id(u)}'


def _safe_obj_id(o: Any) -> Optional[str]:
    if o is None:
        return None
    for attr in ('_id', 'id', 'guid', 'guids', 'pk'):
        if hasattr(o, attr):
            try:
                val = getattr(o, attr)
                if hasattr(val, 'first'):
                    g = val.first()
                    if g and hasattr(g, '_id'):
                        return g._id
                if isinstance(val, (str, int)):
                    return str(val)
            except Exception:
                pass
    return f'obj:{id(o)}'


@contextlib.contextmanager
def assert_notification(
    *,
    type,                       # NotificationType, NotificationType.Type, or str
    user: Any = None,           # optional user object to match
    subscribed_object: Any = None,  # optional object (e.g., node) to match
    times: int = 1,             # exact number of emits expected
    at_least: bool = False,     # if True, assert >= times instead of == times
    assert_email: Optional[bool] = None,  # True: must send email; False: must not; None: ignore
    passthrough: bool = False   # pass emails through to real senders if desired
):
    """
    Usage:
        with assert_notification(type=NotificationType.Type.NODE_FORK_COMPLETED, user=self.user):
            <code that emits>

    Options:
        - subscribed_object=<node>
        - times=2 or at_least=True
        - assert_email=True / False / None
        - passthrough=True to let real email senders run (still captured)
    """
    expected_type = _notif_type_name(type)
    expected_user_id = _safe_user_id(user) if user is not None else None
    expected_obj_id = _safe_obj_id(subscribed_object) if subscribed_object is not None else None

    # Capture emits (and optionally email) while the code under test runs
    with capture_notifications(capture_email=(assert_email is not False), passthrough=passthrough) as cap:
        yield cap

    # ---- Filter emits by criteria ----
    def _emit_matches(e) -> bool:
        # e = {'type': <str>, 'args': (), 'kwargs': {...}}
        if expected_type and str(e.get('type', '')).strip().lower() != expected_type:
            return False
        kw = e.get('kwargs', {})
        # Match user if requested
        if user is not None:
            u = kw.get('user')
            if u is None:
                return False
            if _safe_user_id(u) != expected_user_id:
                return False
        # Match subscribed_object if requested
        if subscribed_object is not None:
            so = kw.get('subscribed_object')
            if so is None:
                return False
            if _safe_obj_id(so) != expected_obj_id:
                return False
        return True

    matching_emits = [e for e in cap.get('emits', []) if _emit_matches(e)]
    count = len(matching_emits)

    if at_least:
        assert count >= times, (
            f'Expected at least {times} emits of type "{expected_type}"'
            f'{f" for user {expected_user_id}" if user is not None else ""}'
            f'{f" and object {expected_obj_id}" if subscribed_object is not None else ""}, '
            f'but saw {count}. All emits: {cap.get("emits", [])}'
        )
    else:
        assert count == times, (
            f'Expected exactly {times} emits of type "{expected_type}"'
            f'{f" for user {expected_user_id}" if user is not None else ""}'
            f'{f" and object {expected_obj_id}" if subscribed_object is not None else ""}, '
            f'but saw {count}. All emits: {cap.get("emits", [])}'
        )

    # ---- Optional email assertions ----
    if assert_email is not None:
        def _email_matches(rec) -> bool:
            # rec['notification_type'] should be the NotificationType model instance used to render
            nt = rec.get('notification_type')
            name = getattr(nt, 'name', None)
            if not name:
                return False
            if name.strip().lower() != expected_type:
                return False
            if user is not None:
                # 'to' can be address string or list in your capture; tolerate both
                to_field = rec.get('to')
                # If we captured the actual user object (e.g., sendgrid path), compare user id
                if hasattr(to_field, '_id') or hasattr(to_field, 'id'):
                    return _safe_user_id(to_field) == expected_user_id
                # Otherwise it's probably an email address; we can't reliably match to user, so just accept type match
            return True

        email_matches = [r for r in cap.get('emails', []) if _email_matches(r)]
        if assert_email:
            assert email_matches, (
                f'Expected an email for notification "{expected_type}"'
                f'{f" to user {expected_user_id}" if user is not None else ""} '
                f'but none were captured. All emails: {cap.get("emails", [])}'
            )
        else:
            assert not email_matches, (
                f'Expected NO email for notification "{expected_type}"'
                f'{f" to user {expected_user_id}" if user is not None else ""} '
                f'but captured: {email_matches}'
            )
