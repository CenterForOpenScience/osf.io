import re, html as html_lib, difflib
import copy
from collections import Counter
import datetime
import functools
from unittest import mock, SkipTest  # added SkipTest import
import requests
import waffle
import contextlib
from typing import Any, Optional

from django.apps import apps
from django.http import HttpRequest
from django.utils import timezone

from framework.auth import Auth
from framework.celery_tasks.handlers import celery_teardown_request
from osf.email import _render_email_html
from osf_tests.factories import DraftRegistrationFactory
from osf.models import Sanction, NotificationType, Notification
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
    """Ensure a log is added during a unit test."""
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
    """Ensure a preprint log is added during a unit test."""
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
def assert_latest_log(log_action, node, index=0):
    """Assert the latest log on `node` matches `log_action`."""
    last_log = node.logs.latest()
    node.reload()
    yield
    # Prefer `date` if present on last_log, otherwise `created`
    if hasattr(last_log, 'date'):
        new_log = node.logs.order_by('-date')[index]
    else:
        new_log = node.logs.order_by('-created')[index]
    assert last_log._id != new_log._id
    assert new_log.action == log_action


@contextlib.contextmanager
def assert_latest_log_not(log_action, node, index=0):
    """Assert the latest log on `node` does NOT match `log_action`."""
    last_log = node.logs.latest()
    node.reload()
    yield
    if hasattr(last_log, 'date'):
        new_log = node.logs.order_by('-date')[index]
    else:
        new_log = node.logs.order_by('-created')[index]
    assert new_log.action != log_action
    assert last_log._id == new_log._id


@contextlib.contextmanager
def mock_archive(project, schema=None, auth=None, draft_registration=None, parent=None,
                 embargo=False, embargo_end_date=None,
                 retraction=False, justification=None, autoapprove_retraction=False,
                 autocomplete=True, autoapprove=False):
    """
    Context manager to create a registration without archiver side effects.
    """
    schema = schema or get_default_metaschema()
    auth = auth or Auth(project.creator)
    draft_registration = draft_registration or DraftRegistrationFactory(
        branched_from=project, registration_schema=schema
    )

    with mock.patch('framework.celery_tasks.handlers.enqueue_task'):
        registration = draft_registration.register(auth=auth, save=True)

    if embargo:
        embargo_end_date = embargo_end_date or (timezone.now() + datetime.timedelta(days=20))
        registration.root.embargo_registration(project.creator, embargo_end_date)
    else:
        registration.root.require_approval(project.creator)

    if autocomplete:
        root_job = registration.root.archive_job
        root_job.status = ARCHIVER_SUCCESS
        root_job.sent = False
        root_job.done = True
        root_job.save()
        # Ensure patches actually apply:
        with mock.patch.object(root_job, 'archive_tree_finished', mock.Mock(return_value=True)), \
             mock.patch('website.archiver.tasks.archive_success.delay', mock.Mock()):
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
    http_request.method = 'GET'
    http_request.path = '/'
    http_request.META['SERVER_NAME'] = 'localhost'
    http_request.META['SERVER_PORT'] = '8000'  # ensure string
    return Request(http_request, *args, **kwargs)


def make_drf_request_with_version(version='2.0', *args, **kwargs):
    req = make_drf_request(*args, **kwargs)
    req.parser_context.setdefault('kwargs', {})
    req.parser_context['kwargs']['version'] = 'v2'
    req.version = version
    return req


class MockAuth:
    def __init__(self, user):
        self.user = user
        self.logged_in = True
        self.private_key = None
        self.private_link = None


mock_auth = lambda user: mock.patch(
    'framework.auth.Auth.from_kwargs',
    mock.Mock(return_value=MockAuth(user))
)


def unique(factory):
    """
    Turn a factory function into one that guarantees unique return values.
    """
    used = []
    @functools.wraps(factory)
    def wrapper():
        item = factory()
        attempts = 0
        while item in used:
            if attempts > 100:
                raise RuntimeError('Tried 100 times to generate a unique value, stopping.')
            item = factory()
            attempts += 1
        used.append(item)
        return item
    return wrapper


@contextlib.contextmanager
def run_celery_tasks():
    yield
    celery_teardown_request()


# Matches a wide range of ISO-like datetimes (with optional microseconds and timezone)
_ISO_DT = re.compile(
    r'\b\d{4}-\d{2}-\d{2}[ T]'
    r'\d{2}:\d{2}:\d{2}(?:\.\d+)?'
    r'(?:Z|[+-]\d{2}:?\d{2}|[+-]\d{4}|(?:\s*UTC)|(?:\s*\+\d{2}:\d{2}))?\b'
)

# Matches tuple-ish renderings like: ('2025-09-02 11:58:52.741685+00:00',)
_TUPLE_WRAP = re.compile(r"\(\s*'([^']+)'\s*,?\s*\)")

def _canon_html(s: str) -> str:
    s = html_lib.unescape(s or '')
    # normalize newlines/whitespace around tags
    s = s.replace('\r\n', '\n').replace('\r', '\n')
    s = re.sub(r'>\s+<', '><', s)
    s = re.sub(r'\s+', ' ', s).strip()

    # 1) unwrap tuple-like timestamp values: ('…',) -> …
    s = _TUPLE_WRAP.sub(r'\1', s)

    # 2) normalize any iso-ish datetime to a stable token
    s = _ISO_DT.sub('<<TS>>', s)

    return s

@contextlib.contextmanager
def capture_notifications(capture_email: bool = True, passthrough: bool = False, expect_none: bool = False):
    """
    Capture NotificationType.emit calls and (optionally) email sends.
    Surfaces helpful template errors if rendering fails.
    """
    try:
        from osf.email import _extract_vars as _extract_template_vars
    except Exception:
        _extract_template_vars = None

    NotificationTypeModel = apps.get_model('osf', 'NotificationType')
    captured = {'emits': [], 'emails': []}

    # Patch the instance method so ALL emit paths are captured
    _real_emit = NotificationTypeModel.emit

    def _wrapped_emit(self, *emit_args, **emit_kwargs):
        # deep-copy dict-like contexts so later mutations won’t affect captures
        ek = dict(emit_kwargs)
        if isinstance(ek.get('event_context'), dict):
            ek['event_context'] = copy.deepcopy(ek['event_context'])
        if isinstance(ek.get('email_context'), dict):
            ek['email_context'] = copy.deepcopy(ek['email_context'])

        captured['emits'].append({
            'type': getattr(self, 'name', None),
            'args': emit_args,
            'kwargs': ek,
            '_is_digest': ek.get('is_digest'),
        })
        if passthrough:
            return _real_emit(self, *emit_args, **ek)

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

    if expect_none:
        if captured['emits']:
            raise AssertionError(
                f'{len(captured['emails'])} notifications were emitted. '
                'Expected at 0'
            )
        return
    if not captured['emits']:
        raise AssertionError(
            'No notifications were emitted. '
            'Expected at least one call to NotificationType.emit. '
            'Tip: ensure your code path triggers an emit and that patches did not get overridden.'
        )

    # Validate each captured emit renders (to catch missing template vars early)
    for idx, rec in enumerate(captured.get('emits', []), start=1):
        nt = NotificationType.objects.get(name=rec.get('type'))
        template_text = getattr(nt, 'template', '') or ''
        ctx = rec['kwargs'].get('event_context', {}) or {}
        try:
            rendered = _render_email_html(nt, ctx)
        except Exception as e:
            # Try to hint at missing variables if possible
            missing_hint = ''
            if _extract_template_vars and isinstance(ctx, dict):
                try:
                    needed = set(_extract_template_vars(template_text))
                    missing = sorted(v for v in needed if v not in ctx)
                    if missing:
                        missing_hint = f' Missing variables: {missing}.'
                except Exception:
                    pass
            raise AssertionError(
                f'Email render failed for notification "{getattr(nt, "name", "(unknown)")}" '
                f'with error: {type(e).__name__}: {e}.{missing_hint}'
            ) from e

        # Fail if rendering produced nothing
        if not isinstance(rendered, str) or not rendered.strip():
            missing_hint = ''
            if _extract_template_vars and isinstance(ctx, dict):
                try:
                    needed = set(_extract_template_vars(template_text))
                    missing = sorted(v for v in needed if v not in ctx)
                    if missing:
                        missing_hint = f' Likely missing variables: {missing}.'
                except Exception:
                    pass
            raise AssertionError(
                f'Email render produced empty/blank HTML for notification "{getattr(nt, "name", "(unknown)")}".'
                f'{missing_hint}'
            )

        # Fail if rendering just echoed the raw template text (Mako likely failed)
        if template_text and rendered.strip() == template_text.strip():
            raise AssertionError(
                f'Email render returned the raw template (no interpolation) for '
                f'"{getattr(nt, "name", "(unknown)")}"; template rendering likely failed.'
            )

@contextlib.contextmanager
def capture_notifications_or_not(
    capture_email: bool = True,
    passthrough: bool = False,
    allow_none: bool = True,
):
    """
    Variant of capture_notifications that *allows* cases where no NotificationType.emit
    calls occur, instead of raising an AssertionError.

    Args:
        capture_email (bool): Whether to capture email send calls (default True).
        passthrough (bool): If True, calls real emit/send methods as well.
        allow_none (bool): If True, do not raise if no notifications are emitted.
    """
    try:
        from osf.email import _extract_vars as _extract_template_vars
    except Exception:
        _extract_template_vars = None

    NotificationTypeModel = apps.get_model('osf', 'NotificationType')
    captured = {'emits': [], 'emails': []}

    # Patch emit
    _real_emit = NotificationTypeModel.emit

    def _wrapped_emit(self, *emit_args, **emit_kwargs):
        ek = dict(emit_kwargs)
        if isinstance(ek.get('event_context'), dict):
            ek['event_context'] = copy.deepcopy(ek['event_context'])
        if isinstance(ek.get('email_context'), dict):
            ek['email_context'] = copy.deepcopy(ek['email_context'])
        captured['emits'].append({
            'type': getattr(self, 'name', None),
            'args': emit_args,
            'kwargs': ek,
            '_is_digest': ek.get('is_digest'),
        })
        if passthrough:
            return _real_emit(self, *emit_args, **ek)

    patches = [mock.patch('osf.models.notification_type.NotificationType.emit', new=_wrapped_emit)]

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

    # If no notifications were emitted, skip validation when allowed
    if not captured['emits']:
        if not allow_none:
            raise AssertionError(
                'No notifications were emitted. Expected at least one call to NotificationType.emit.'
            )
        return

    # Template rendering validation
    for rec in captured['emits']:
        nt = NotificationType.objects.get(name=rec.get('type'))
        template_text = getattr(nt, 'template', '') or ''
        ctx = rec['kwargs'].get('event_context', {}) or {}
        try:
            rendered = _render_email_html(nt, ctx)
        except Exception as e:
            missing_hint = ''
            if _extract_template_vars and isinstance(ctx, dict):
                try:
                    needed = set(_extract_template_vars(template_text))
                    missing = sorted(v for v in needed if v not in ctx)
                    if missing:
                        missing_hint = f' Missing variables: {missing}.'
                except Exception:
                    pass
            raise AssertionError(
                f'Email render failed for notification "{nt.name}" '
                f'with error: {type(e).__name__}: {e}.{missing_hint}'
            ) from e

        if not isinstance(rendered, str) or not rendered.strip():
            raise AssertionError(
                f'Email render produced empty or blank HTML for notification "{nt.name}".'
            )

        if template_text and rendered.strip() == template_text.strip():
            raise AssertionError(
                f'Email render returned the raw template (no interpolation) for "{nt.name}".'
            )

def get_mailhog_messages():
    """Fetch messages from MailHog API."""
    if not waffle.switch_is_active(features.ENABLE_MAILHOG):
        return {'count': 0, 'items': []}
    mailhog_url = f'{website_settings.MAILHOG_API_HOST}/api/v2/messages'
    response = requests.get(mailhog_url)
    if response.status_code == 200:
        return response.json()
    return {'count': 0, 'items': []}


def delete_mailhog_messages():
    """Delete all messages from MailHog."""
    if not waffle.switch_is_active(features.ENABLE_MAILHOG):
        return
    mailhog_url = f'{website_settings.MAILHOG_API_HOST}/api/v1/messages'
    requests.delete(mailhog_url)


def assert_emails(mailhog_messages, notifications):
    """
    Compare rendered expected HTML vs MailHog actual HTML in a deterministic way.
    We sort by recipient to avoid flaky ordering differences.
    """
    # Build expected list [(recipient, html)]
    expected = []
    expected_digest = []

    for item in notifications['emits']:
        to_username = item['kwargs']['user'].username
        nt = NotificationType.objects.get(name=item['type'])
        html = _render_email_html(nt, item['kwargs']['event_context'])
        if item.get('_is_digest'):
            expected_digest.append((to_username, nt))
        else:
            expected.append((to_username, _canon_html(html)))

    # Build actual list [(recipient, html)]
    actual = []
    for msg in mailhog_messages.get('items', []):
        to_addr = msg['Content']['Headers']['To'][0]
        body = msg['Content']['Body']
        actual.append((to_addr, _canon_html(body)))

    # Sort and compare
    expected_sorted = sorted(expected, key=lambda x: x[0])
    actual_sorted = sorted(actual, key=lambda x: x[0])

    exp_html = [h for _, h in expected_sorted]
    act_html = [h for _, h in actual_sorted]
    exp_to = [r for r, _ in expected_sorted]
    act_to = [r for r, _ in actual_sorted]

    if exp_html != act_html:
        # helpful diff for the first mismatch
        for i, (eh, ah) in enumerate(zip(exp_html, act_html)):
            if eh != ah:
                diff = '\n'.join(difflib.unified_diff(eh.split(), ah.split(), lineterm=''))
                raise AssertionError(
                    f"Rendered HTML bodies differ (sorted by recipient) at index {i} "
                    f"({exp_to[i]}):\n{diff}"
                )
    assert exp_to == act_to, 'Recipient lists differ (sorted).'

    digest_notifications_qs = Notification.objects.filter(sent__isnull=True)

    if expected_digest:
        assert len(expected_digest) == digest_notifications_qs.count()
        for to_username, nt in expected_digest:
            assert digest_notifications_qs.filter(subscription__user__username=to_username, subscription__notification_type=nt).exists()


def _notif_type_name(t: Any) -> str:
    """Normalize a NotificationType-ish input to its lowercase name."""
    if t is None:
        return ''
    n = getattr(t, 'name', None)
    if n:
        return str(n).strip().lower()
    for attr in ('value', 'NAME', 'name'):
        if hasattr(t, attr):
            try:
                return str(getattr(t, attr)).strip().lower()
            except Exception:
                pass
    return str(t).strip().lower()


def _safe_user_id(user: Any) -> Optional[str]:
    """Normalize a user object to a stable identifier."""
    if user is None:
        return None

    for attr in ('_id', 'id', 'guids', 'guid', 'pk'):
        if hasattr(user, attr):
            try:
                value = getattr(user, attr)
                if hasattr(value, 'first'):
                    guid = value.first()
                    if guid and hasattr(guid, '_id'):
                        return guid._id
                if isinstance(value, (str, int)):
                    return str(value)
            except Exception:
                pass

    return f'obj:{id(user)}'


def _safe_obj_id(obj: Any) -> Optional[str]:
    """Normalize an object to a stable identifier."""
    if obj is None:
        return None

    for attr in ('_id', 'id', 'guid', 'guids', 'pk'):
        if hasattr(obj, attr):
            try:
                value = getattr(obj, attr)
                if hasattr(value, 'first'):
                    guid = value.first()
                    if guid and hasattr(guid, '_id'):
                        return guid._id
                if isinstance(value, (str, int)):
                    return str(value)
            except Exception:
                pass

    return f'obj:{id(obj)}'


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
    """
    expected_type = _notif_type_name(type)
    expected_user_id = _safe_user_id(user) if user is not None else None
    expected_obj_id = _safe_obj_id(subscribed_object) if subscribed_object is not None else None

    # Capture emits (and optionally email) while the code under test runs
    with capture_notifications(capture_email=(assert_email is not False), passthrough=passthrough) as cap:
        yield cap

    # ---- Filter emits by criteria ----
    def _emit_matches(e) -> bool:
        if expected_type and str(e.get('type', '')).strip().lower() != expected_type:
            return False
        kw = e.get('kwargs', {})
        if user is not None:
            u = kw.get('user')
            if u is None or _safe_user_id(u) != expected_user_id:
                return False
        if subscribed_object is not None:
            so = kw.get('subscribed_object')
            if so is None or _safe_obj_id(so) != expected_obj_id:
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
            nt = rec.get('notification_type')
            name = getattr(nt, 'name', None)
            if not name or name.strip().lower() != expected_type:
                return False
            if user is not None:
                to_field = rec.get('to')
                if hasattr(to_field, '_id') or hasattr(to_field, 'id'):
                    return _safe_user_id(to_field) == expected_user_id
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
