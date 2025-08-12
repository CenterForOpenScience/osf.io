import os
import re
import json
import waffle
import logging
from html import unescape

from django.core.mail import EmailMessage, get_connection

from mako.template import Template as MakoTemplate
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
from api.base.settings import CI_ENV

# --- Point lookup at the *templates root* ---
_BASE = getattr(settings, 'BASE_PATH', '')
TEMPLATE_ROOT = os.path.join(_BASE, 'website', 'templates')
EMAIL_TEMPLATE_DIRS = getattr(settings, 'EMAIL_TEMPLATE_DIRS', [TEMPLATE_ROOT])
EMAIL_TEMPLATE_DIRS = [os.path.abspath(p) for p in EMAIL_TEMPLATE_DIRS]

MAKO_LOOKUP = TemplateLookup(
    directories=EMAIL_TEMPLATE_DIRS,
    input_encoding='utf-8',
)

def _detect_email_folder() -> str:
    """Return 'emails' or 'notifications' based on where notify_base.mako exists (default 'emails')."""
    for folder in ('emails', 'notifications'):
        if os.path.exists(os.path.join(TEMPLATE_ROOT, folder, 'notify_base.mako')):
            return folder
        for root in EMAIL_TEMPLATE_DIRS:
            if os.path.exists(os.path.join(root, folder, 'notify_base.mako')):
                return folder
    return 'emails'

_EMAIL_FOLDER = _detect_email_folder()

def _render_email_html(template_text: str, ctx: dict, folder: str | None = None) -> str:
    """Render a DB-backed Mako template that may <%inherit file="notify_base.mako">.
    We give it a virtual URI inside the folder that contains notify_base.mako so
    the relative inherit resolves to /<folder>/notify_base.mako.
    """
    if not template_text:
        return ''
    folder = folder or _EMAIL_FOLDER
    uri = f'/{folder}/inline_{abs(hash(template_text))}.mako'
    try:
        return MakoTemplate(text=template_text, lookup=MAKO_LOOKUP, uri=uri).render(**ctx)
    except Exception:
        logging.exception('Mako render failed; returning raw template')
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

# ---------------- SMTP path ----------------
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

# ---------------- SendGrid path ----------------
def send_email_with_send_grid(to_addr, notification_type, context, email_context=None):
    if not settings.SENDGRID_API_KEY:
        raise NotImplementedError('SENDGRID_API_KEY is required for sendgrid notifications.')

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

    # Render ONCE with lookup + proper virtual URI
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
            {'type': 'text/plain', 'value': text},   # plain first
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
