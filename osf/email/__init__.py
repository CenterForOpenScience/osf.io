import os
import re
import json
import logging
import importlib
import sys
from html import unescape
from typing import List, Optional
from mako.template import Template as MakoTemplate


import waffle
from django.core.mail import EmailMessage, get_connection

from mako.lookup import TemplateLookup
from pytest_socket import SocketConnectBlockedError

from sendgrid import SendGridAPIClient
from python_http_client.exceptions import (
    BadRequestsError as SGBadRequestsError,
    HTTPError as SGHTTPError,
    UnauthorizedError as SGUnauthorizedError,
    ForbiddenError as SGForbiddenError,
)

from osf import features
from website import settings

def _existing_dirs(paths: List[str]) -> List[str]:
    out = []
    seen = set()
    for p in paths:
        if not p:
            continue
        ap = os.path.abspath(p)
        tail = os.path.basename(ap.rstrip(os.sep))
        if tail in ('emails', 'notifications'):
            ap = os.path.dirname(ap)
        if os.path.isdir(ap) and ap not in seen:
            out.append(ap)
            seen.add(ap)
    return out

def _default_template_roots() -> List[str]:
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

    return _existing_dirs(roots)

LOOKUP_DIRS = _default_template_roots()
MAKO_LOOKUP = TemplateLookup(directories=LOOKUP_DIRS, input_encoding='utf-8')

def _discover_notify_base_uri() -> Optional[str]:
    for root in LOOKUP_DIRS:
        for folder in ('emails', 'notifications', ''):
            p = os.path.join(root, folder, 'notify_base.mako')
            if os.path.exists(p):
                rel = os.path.relpath(p, root).replace(os.sep, '/')
                return '/' + rel
    for root in LOOKUP_DIRS:
        for dirpath, _, files in os.walk(root):
            if 'notify_base.mako' in files:
                rel = os.path.relpath(os.path.join(dirpath, 'notify_base.mako'), root).replace(os.sep, '/')
                return '/' + rel
    return None

NOTIFY_BASE_URI = _discover_notify_base_uri()
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
    'logo_url': settings.OSF_LOGO,
    'node_url': '',
    'ns_url': '',
    'osf_contact_email': settings.OSF_CONTACT_EMAIL,
    'provider_name': '',
}

def _render_email_html(template_text: str, ctx: dict) -> str:
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

    except Exception:
        logging.exception(
            'Mako render failed. provided_keys=%s inline_uri=%s base_uri=%s lookup_dirs=%s',
            sorted((ctx or {}).keys()), uri, NOTIFY_BASE_URI, LOOKUP_DIRS,
        )
        return template_text

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

def send_email_over_smtp(to_email, notification_type, context, email_context):
    if waffle.switch_is_active(features.ENABLE_MAILHOG):
        host = settings.MAILHOG_HOST
        port = settings.MAILHOG_PORT
    else:
        host = settings.MAIL_SERVER
        port = settings.MAIL_PORT
    if not host or not port:
        raise NotImplementedError('MAIL_SERVER or MAIL_PORT is not set')

    subject = None if not notification_type.subject else notification_type.subject.format(**context)
    body_html = _render_email_html(notification_type.template, context)

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

def send_email_with_send_grid(to_addr, notification_type, context, email_context=None):

    email_context = email_context or {}
    to_list = [to_addr] if isinstance(to_addr, str) else [a for a in (to_addr or []) if a]
    if not to_list:
        logging.error('SendGrid: no recipients after normalization')
        return False

    from_email = getattr(settings, 'SENDGRID_FROM_EMAIL', None) or getattr(settings, 'FROM_EMAIL', None)
    if not from_email:
        logging.error('SendGrid: missing SENDGRID_FROM_EMAIL/FROM_EMAIL')
        return False

    html = _render_email_html(notification_type.template, context) or '<p>(no content)</p>'

    subject_tpl = getattr(notification_type, 'subject', None)
    subject = subject_tpl.format(**context) if subject_tpl else f'Notification: {getattr(notification_type, "name", "OSF")}'

    personalization = {'to': [{'email': addr} for addr in to_list]}
    cc_addr = email_context.get('cc_addr')
    if cc_addr:
        personalization['cc'] = [{'email': a} for a in ([cc_addr] if isinstance(cc_addr, str) else cc_addr)]
    bcc_addr = email_context.get('bcc_addr')
    if bcc_addr:
        personalization['bcc'] = [{'email': a} for a in ([bcc_addr] if isinstance(bcc_addr, str) else bcc_addr)]

    payload = {
        'from': {'email': from_email},
        'subject': subject,
        'personalizations': [personalization],
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

    except (SGUnauthorizedError, SGForbiddenError) as exc:
        body = getattr(exc, 'body', b'')
        try:
            body = body.decode('utf-8', 'ignore') if isinstance(body, (bytes, bytearray)) else str(body)
        except Exception:
            pass
        logging.error('SendGrid auth error (%s): %s', exc.__class__.__name__, body)
        raise

    except SGHTTPError as exc:
        body = getattr(exc, 'body', b'')
        try:
            body = body.decode('utf-8', 'ignore') if isinstance(body, (bytes, bytearray)) else str(body)
        except Exception:
            pass
        logging.error('SendGrid HTTPError: %s | payload=%s', body, payload)
        raise

    except SocketConnectBlockedError as exc:
        if 'pytest' in sys.modules:
            logging.error('You sent an email while in the local test environment, try using `capture_notifications` '
                          'or `assert_notifications` instead')
        else:
            logging.error('SendGrid hit a blocked socket error: %r | payload=%s', exc, payload)
        raise
    except Exception as exc:
        logging.error('SendGrid unexpected error: %r | payload=%s', exc, payload)
        raise
