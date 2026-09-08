import os
import re
import json
import logging
import importlib
import sys
from html import unescape
from typing import Optional
from mako.template import Template as MakoTemplate
import base64


import waffle
from django.core.mail import EmailMessage, get_connection

from mako.lookup import TemplateLookup

from sendgrid import SendGridAPIClient
from python_http_client.exceptions import (
    BadRequestsError as SGBadRequestsError,
    HTTPError as SGHTTPError,
    UnauthorizedError as SGUnauthorizedError,
    ForbiddenError as SGForbiddenError,
)

from osf import features
from website import settings

def collect_existing_directories(paths: list[str]) -> list[str]:
    """Collect and return unique existing directories from the given paths.

    If a path ends with 'emails' or 'notifications', its parent directory
    is used instead. Only directories that exist on disk are included.
    """
    existing_directories = []
    processed_paths = set()

    for path in paths:
        if not path:
            continue

        absolute_path = os.path.abspath(path)
        last_component = os.path.basename(absolute_path.rstrip(os.sep))

        if last_component in ('emails', 'notifications'):
            absolute_path = os.path.dirname(absolute_path)

        if os.path.isdir(absolute_path) and absolute_path not in processed_paths:
            existing_directories.append(absolute_path)
            processed_paths.add(absolute_path)

    return existing_directories

def _default_template_roots() -> list[str]:
    roots = []
    cfg = getattr(settings, 'EMAIL_TEMPLATE_DIRS', None)
    if cfg:
        roots.extend(cfg if isinstance(cfg, (list, tuple)) else [cfg])

    try:
        website_pkg = importlib.import_module('website')
        base = os.path.abspath(os.path.dirname(website_pkg.__file__))
        roots.append(os.path.join(base, 'templates'))
    except Exception:
        pass

    base_path = getattr(settings, 'BASE_PATH', '')
    if base_path:
        roots.append(os.path.join(base_path, 'website', 'templates'))

    return collect_existing_directories(roots)

LOOKUP_DIRS = _default_template_roots()
MAKO_LOOKUP = TemplateLookup(directories=LOOKUP_DIRS, input_encoding='utf-8')

def _discover_notification_base_uri() -> Optional[str]:
    """Find and return the relative URI path to the first found 'notify_base.mako' template.

    Searches through directories listed in LOOKUP_DIRS, checking common subfolders
    ('emails', 'notifications', and root). Returns the relative path as a URI string,
    or None if no such template is found.
    """
    for lookup_root in LOOKUP_DIRS:
        for subfolder in ('emails', 'notifications', ''):
            candidate_path = os.path.join(lookup_root, subfolder, 'notify_base.mako')
            if os.path.exists(candidate_path):
                relative_path = os.path.relpath(candidate_path, lookup_root).replace(os.sep, '/')
                return '/' + relative_path

    for lookup_root in LOOKUP_DIRS:
        for current_dir, _, files in os.walk(lookup_root):
            if 'notify_base.mako' in files:
                template_path = os.path.join(current_dir, 'notify_base.mako')
                relative_path = os.path.relpath(template_path, lookup_root).replace(os.sep, '/')
                return '/' + relative_path

    return None

NOTIFY_BASE_URI = _discover_notification_base_uri()
if not NOTIFY_BASE_URI:
    logging.error('Email templates: could not locate notify_base.mako. lookup_dirs=%s', LOOKUP_DIRS)
else:
    logging.info('Email templates: notify_base.mako resolved at URI %s (roots=%s)', NOTIFY_BASE_URI, LOOKUP_DIRS)

def _inline_uri_for_db_template() -> str:
    folder = 'emails'
    if NOTIFY_BASE_URI:
        parts = NOTIFY_BASE_URI.strip('/').split('/')
        if len(parts) > 1:
            folder = '/'.join(parts[:-1])
    return f'/{folder}/inline_{os.getpid()}_{id(MAKO_LOOKUP)}.mako'


INHERIT_RX = re.compile(
    r'(<%inherit\s+file=)(["\'])(?:/?(?:emails|notifications)/)?notify_base\.mako\2',
    flags=re.I
)

_VAR_RX = re.compile(r'\$\{\s*([A-Za-z_]\w*)(?:[^\}]*)\}')

def _extract_vars(src: str) -> set[str]:
    return {m.group(1) for m in _VAR_RX.finditer(src or '')}

def _read_lookup_uri(uri: str) -> str:
    """Read template source for a lookup URI using LOOKUP_DIRS."""
    if not uri:
        return ''
    rel = uri.lstrip('/')
    for root in LOOKUP_DIRS:
        p = os.path.join(root, rel)
        if os.path.exists(p):
            try:
                with open(p, 'r', encoding='utf-8') as f:
                    return f.read()
            except Exception:
                pass
    return ''


NOTIFY_BASE_DEFAULTS = {
    'logo': settings.OSF_LOGO,  # matches default in notify_base.mako
    'logo_url': None,
    'node_url': '',
    'ns_url': '',
    'osf_contact_email': settings.OSF_CONTACT_EMAIL,
    'provider_name': '',
    'osf_logo_list': settings.OSF_LOGO_LIST,
    'OSF_LOGO_LIST': settings.OSF_LOGO_LIST,
    'domain': settings.DOMAIN,
}

def _render_email_html(notification_type, ctx: dict, return_original_error: bool = False) -> str:
    template_text = notification_type.template
    if not template_text:
        return ''

    uri = _inline_uri_for_db_template()
    text = template_text
    if NOTIFY_BASE_URI:
        text = INHERIT_RX.sub(rf'\1\2{NOTIFY_BASE_URI}\2', text, count=1)

    # If using notify_base, merge in defaults
    if 'notify_base' in text or 'notify_base' in (uri or ''):
        for k, v in NOTIFY_BASE_DEFAULTS.items():
            ctx.setdefault(k, v)

    try:
        return MakoTemplate(
            text=text,
            lookup=MAKO_LOOKUP,
            uri=uri,
            strict_undefined=True,
        ).render(**(ctx or {}))

    except Exception as e:
        if return_original_error:
            raise e
        logging.exception(
            f'Mako render failed. type {notification_type.name} provided_keys=%s inline_uri=%s base_uri=%s lookup_dirs=%s',
            sorted((ctx or {}).keys()), uri, NOTIFY_BASE_URI, LOOKUP_DIRS,
        )
        raise Exception(f'Failed to render email template {notification_type.name}')

def _strip_html(html: str) -> str:
    if not html:
        return ''
    text = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', html, flags=re.S | re.I)
    text = re.sub(r'<br\s*/?>', '\n', text, flags=re.I)
    text = re.sub(r'</p\s*>', '\n\n', text, flags=re.I)
    text = re.sub(r'<[^>]+>', '', text)
    return unescape(re.sub(r'\n{3,}', '\n\n', text)).strip() or '(no content)'

def _safe_categories(cats):
    out = []
    for c in (cats or []):
        if isinstance(c, str):
            c = c.strip()
            if c and len(c) <= 255 and re.fullmatch(r'[\x20-\x7E]+', c):
                out.append(c)
    return out[:10]

def send_email_over_smtp(to_email, notification_type, context, email_context, rendered_html=None):
    if waffle.switch_is_active(features.ENABLE_MAILHOG):
        host = settings.MAILHOG_HOST
        port = settings.MAILHOG_PORT
    else:
        host = settings.MAIL_SERVER
        port = settings.MAIL_PORT
    if not host or not port:
        if settings.DEBUG:
            return
        raise NotImplementedError('MAIL_SERVER or MAIL_PORT is not set')

    subject = None if not notification_type.subject else notification_type.subject.format(**context)
    body_html = rendered_html or _render_email_html(notification_type, context) or '<p>(no content)</p>'

    email = EmailMessage(
        subject=subject,
        body=body_html,
        from_email=settings.OSF_SUPPORT_EMAIL,
        to=[to_email],
        connection=get_connection(
            backend='django.core.mail.backends.smtp.EmailBackend',
            host=host,
            port=port,
            username=settings.MAIL_USERNAME,
            password=settings.MAIL_PASSWORD,
            use_tls=False,
            use_ssl=False,
        )
    )
    email.content_subtype = 'html'

    if email_context:
        attachment_name = email_context.get('attachment_name')
        attachment_content = email_context.get('attachment_content')
        if attachment_name and attachment_content:
            email.attach(attachment_name, attachment_content)
    email.send()

def _email_objects(addrs):
    if not addrs:
        return None
    if isinstance(addrs, str):
        addrs = [addrs]
    return [{'email': a} for a in addrs]


def _build_sendgrid_personalizations(to_list, email_context=None, is_multiple=False):
    """Build SendGrid personalizations.

    When ``is_multiple`` is True, each address gets its own personalization (separate
    delivery; recipients do not see each other).

    Optional ``email_context`` keys:
    - ``custom_args``: dict applied to every personalization
    - ``custom_args_list``: list of dicts parallel to ``to_list`` (used when
      ``is_multiple`` is True; each entry is attached to that recipient only)
    """
    email_context = email_context or {}
    cc = _email_objects(email_context.get('cc_addr'))
    bcc = _email_objects(email_context.get('bcc_addr'))
    shared_custom_args = email_context.get('custom_args')
    custom_args_list = email_context.get('custom_args_list') or []

    def personalization(recipients, custom_args=None):
        item = {'to': [{'email': a} for a in recipients]}
        if cc:
            item['cc'] = cc
        if bcc:
            item['bcc'] = bcc
        if custom_args:
            item['custom_args'] = {str(k): str(v) for k, v in custom_args.items()}
        return item

    if not is_multiple:
        return [personalization(to_list, shared_custom_args)]

    return [
        personalization([addr], custom_args_list[i])
        for i, addr in enumerate(to_list)
    ]


def send_email_with_send_grid(to_addr, notification_type, context, email_context=None, *, is_multiple=False, rendered_html=None):

    email_context = email_context or {}
    to_list = [to_addr] if isinstance(to_addr, str) else [a for a in (to_addr or []) if a]
    if not to_list:
        logging.error('SendGrid: no recipients after normalization')
        return False

    from_email = getattr(settings, 'SENDGRID_FROM_EMAIL', None) or getattr(settings, 'FROM_EMAIL', None)
    if not from_email:
        logging.error('SendGrid: missing SENDGRID_FROM_EMAIL/FROM_EMAIL')
        return False

    html = rendered_html or _render_email_html(notification_type, context) or '<p>(no content)</p>'

    subject_tpl = getattr(notification_type, 'subject', None)
    subject = subject_tpl.format(**context) if subject_tpl else f'Notification: {getattr(notification_type, "name", "OSF")}'

    payload = {
        'from': {'email': from_email},
        'subject': subject,
        'personalizations': _build_sendgrid_personalizations(
            to_list, email_context=email_context, is_multiple=is_multiple
        ),
        'content': [
            {'type': 'text/html', 'value': html},
        ],
    }

    reply_to = email_context.get('reply_to')
    if reply_to:
        payload['reply_to'] = {'email': reply_to}

    cats = _safe_categories(email_context.get('email_categories'))
    if cats:
        payload['categories'] = cats

    if email_context:
        attachment_name = email_context.get('attachment_name')
        attachment_content = email_context.get('attachment_content')
        if attachment_name and attachment_content:

            encoded = base64.b64encode(attachment_content).decode('ascii')

            item = {
                'content': encoded,
                'filename': attachment_name,
                'disposition': 'attachment',
            }

            payload['attachments'] = [item]
    try:
        sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
        resp = sg.client.mail.send.post(request_body=payload)
        if resp.status_code not in (200, 201, 202):
            logging.error(
                'SendGrid non-2xx: code=%s body=%s payload=%s',
                resp.status_code,
                getattr(resp, 'body', b'').decode('utf-8', 'ignore'),
                payload
            )
            resp.raise_for_status()
        logging.info('Notification email sent to %s for %s.', to_list, getattr(notification_type, 'name', str(notification_type)))
        return True

    except SGBadRequestsError as exc:
        body = None
        try:
            body = exc.body.decode('utf-8', 'ignore') if isinstance(exc.body, (bytes, bytearray)) else str(exc.body)
            parsed = json.loads(body)
        except Exception:
            parsed = {'raw_body': body}
        logging.error('SendGrid 400 Bad Request: %s | payload=%s', parsed, payload)
        if isinstance(parsed, dict) and 'errors' in parsed:
            for err in parsed['errors']:
                logging.error('SendGrid error: message=%r field=%r help=%r',
                              err.get('message'), err.get('field'), err.get('help'))
        raise

    except (SGUnauthorizedError, SGForbiddenError, SGHTTPError) as exc:
        body = getattr(exc, 'body', b'')
        try:
            body = body.decode('utf-8', 'ignore') if isinstance(body, (bytes, bytearray)) else str(body)
        except Exception:
            pass
        logging.error('SendGrid error (%s): %s', exc.__class__.__name__, body)
        raise
    except Exception as exc:
        if 'pytest' in sys.modules:
            logging.error(f'You sent an email of {notification_type.name} while in the local test environment, try'
                          f' using `capture_notifications` or `assert_notifications` instead')
        else:
            logging.error('SendGrid hit a blocked socket error: %r | payload=%s', exc, payload)
        raise

def send_email(recipient_address, notification_type, event_context=None, email_context=None, rendered_html=None):
    """
    Send an email using either SMTP or SendGrid based on settings and feature flags.
    """
    if waffle.switch_is_active(features.ENABLE_MAILHOG):
        send_email_over_smtp(
            recipient_address,
            notification_type,
            event_context,
            email_context,
            rendered_html=rendered_html,
        )

    if not settings.LOCAL_MODE:
        send_email_with_send_grid(
            recipient_address,
            notification_type,
            event_context,
            email_context,
            rendered_html=rendered_html,
        )

    if settings.LOCAL_MODE and not waffle.switch_is_active(features.ENABLE_MAILHOG):
        logging.warning(
            'Both ENABLE_MAILHOG and LOCAL_MODE are disabled. Emails will not be sent to MailHog or real email addresses. '
            'Turn on ENABLE_MAILHOG to send emails to MailHog for testing, or turn on LOCAL_MODE to send emails with SendGrid.'
        )
