import os
import re
import json
import logging
import importlib
from html import unescape
from typing import List, Optional

import waffle
from django.core.mail import EmailMessage, get_connection

from mako.template import Template as MakoTemplate
from mako.lookup import TemplateLookup
from mako.exceptions import TopLevelLookupException

from sendgrid import SendGridAPIClient
from python_http_client.exceptions import (
    BadRequestsError as SGBadRequestsError,
    HTTPError as SGHTTPError,
    UnauthorizedError as SGUnauthorizedError,
    ForbiddenError as SGForbiddenError,
)

from osf import features
from website import settings
from api.base.settings import CI_ENV

def _existing_dirs(paths: List[str]) -> List[str]:
    out = []
    seen = set()
    for p in paths:
        if not p:
            continue
        ap = os.path.abspath(p)
        # If user passed .../emails or .../notifications, lift to its parent templates root
        tail = os.path.basename(ap.rstrip(os.sep))
        if tail in ('emails', 'notifications'):
            ap = os.path.dirname(ap)
        if os.path.isdir(ap) and ap not in seen:
            out.append(ap)
            seen.add(ap)
    return out

def _default_template_roots() -> List[str]:
    roots = []
    # 1) settings.EMAIL_TEMPLATE_DIRS (if provided)
    cfg = getattr(settings, 'EMAIL_TEMPLATE_DIRS', None)
    if cfg:
        roots.extend(cfg if isinstance(cfg, (list, tuple)) else [cfg])

    # 2) website package path (most reliable)
    try:
        website_pkg = importlib.import_module('website')
        base = os.path.abspath(os.path.dirname(website_pkg.__file__))
        roots.append(os.path.join(base, 'templates'))
    except Exception:
        pass

    # 3) settings.BASE_PATH fallback
    base_path = getattr(settings, 'BASE_PATH', '')
    if base_path:
        roots.append(os.path.join(base_path, 'website', 'templates'))

    return _existing_dirs(roots)

LOOKUP_DIRS = _default_template_roots()
MAKO_LOOKUP = TemplateLookup(directories=LOOKUP_DIRS, input_encoding='utf-8')

def _discover_notify_base_uri() -> Optional[str]:
    # Try common locations quickly
    for root in LOOKUP_DIRS:
        for folder in ('emails', 'notifications', ''):
            p = os.path.join(root, folder, 'notify_base.mako')
            if os.path.exists(p):
                rel = os.path.relpath(p, root).replace(os.sep, '/')
                return '/' + rel
    # Deep search
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

def _render_email_html(template_text: str, ctx: dict) -> str:
    if not template_text:
        return ''
    uri = _inline_uri_for_db_template()

    try:
        return MakoTemplate(text=template_text, lookup=MAKO_LOOKUP, uri=uri).render(**ctx)
    except TopLevelLookupException as e:
        if NOTIFY_BASE_URI:
            patched = re.sub(
                r'(<%inherit\s+file=)(["\'])notify_base\.mako\2',
                rf'\1\2{NOTIFY_BASE_URI}\2',
                template_text,
                count=1,
            )
            try:
                return MakoTemplate(text=patched, lookup=MAKO_LOOKUP, uri=uri).render(**ctx)
            except Exception:
                logging.exception(
                    'Mako fallback render failed. base_uri=%s; inline_uri=%s; lookup_dirs=%s',
                    NOTIFY_BASE_URI, uri, LOOKUP_DIRS
                )
                return template_text
        else:
            logging.error(
                'Mako render failed and notify_base.mako not found. inline_uri=%s; lookup_dirs=%s; err=%r',
                uri, LOOKUP_DIRS, e
            )
            return template_text
    except Exception:
        logging.exception(
            'Mako render failed. inline_uri=%s; lookup_dirs=%s',
            uri, LOOKUP_DIRS
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

    if not CI_ENV:
        email.send()

def send_email_with_send_grid(to_addr, notification_type, context, email_context=None):

    email_context = email_context or {}
    to_list = [to_addr] if isinstance(to_addr, str) else [a for a in (to_addr or []) if a]
    if not to_list:
        logging.error('SendGrid: no recipients after normalization')
        return False

    if settings.SENDGRID_WHITELIST_MODE:
        not_allowed = [a for a in to_list if a not in getattr(settings, 'SENDGRID_EMAIL_WHITELIST', ())]
        if not_allowed:
            return False

    from_email = getattr(settings, 'SENDGRID_FROM_EMAIL', None) or getattr(settings, 'FROM_EMAIL', None)
    if not from_email:
        logging.error('SendGrid: missing SENDGRID_FROM_EMAIL/FROM_EMAIL')
        return False

    html = _render_email_html(notification_type.template, context) or '<p>(no content)</p>'
    text = _strip_html(html)

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
            {'type': 'text/plain', 'value': text},
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

    except Exception as exc:
        logging.error('SendGrid unexpected error: %r | payload=%s', exc, payload)
        raise
