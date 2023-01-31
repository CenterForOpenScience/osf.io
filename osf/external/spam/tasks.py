import re
import logging
import requests
from framework.celery_tasks import app as celery_app
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from osf.external.askismet.client import AkismetClient
from osf.external.oopspam.client import OOPSpamClient
from website import settings

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


DOMAIN_REGEX = re.compile(r'\W*(?P<protocol>\w+://)?(?P<www>www\.)?(?P<domain>([\w-]+\.)+[a-zA-Z]+)(?P<path>[/\-\.\w]*)?\W*')
REDIRECT_CODES = {301, 302, 303, 307, 308}


@celery_app.task()
def reclassify_domain_references(notable_domain_id, current_note, previous_note):
    from osf.models.notable_domain import DomainReference, NotableDomain
    domain = NotableDomain.load(notable_domain_id)
    references = DomainReference.objects.filter(domain=domain)
    with transaction.atomic():
        for item in references:
            item.is_triaged = current_note != NotableDomain.Note.UNKNOWN
            if current_note == NotableDomain.Note.EXCLUDE_FROM_ACCOUNT_CREATION_AND_CONTENT:
                item.referrer.confirm_spam(save=False, domains=[domain.domain])
            elif previous_note == NotableDomain.Note.EXCLUDE_FROM_ACCOUNT_CREATION_AND_CONTENT:
                try:
                    item.referrer.spam_data['domains'].remove(domain.domain)
                except (KeyError, AttributeError, ValueError) as error:
                    logger.info(error)
                if not item.referrer.spam_data.get('domains') and not item.referrer.spam_data.get('who_flagged'):
                        item.referrer.unspam(save=False)
            item.save()
            item.referrer.save()

@celery_app.task()
def check_resource_for_domains(guid, content):
    from osf.models import Guid, NotableDomain, DomainReference
    guid = Guid.load(guid)
    if not guid:
        return f'{guid} not found'
    resource = guid.referent
    spammy_domains = []
    referrer_content_type = ContentType.objects.get_for_model(resource)
    for domain in _extract_domains(content):
        notable_domain, _ = NotableDomain.objects.get_or_create(domain=domain)
        if notable_domain.note == NotableDomain.Note.EXCLUDE_FROM_ACCOUNT_CREATION_AND_CONTENT:
            spammy_domains.append(notable_domain.domain)
        DomainReference.objects.get_or_create(
            domain=notable_domain,
            referrer_object_id=resource.id,
            referrer_content_type=referrer_content_type,
            defaults={'is_triaged': notable_domain.note != NotableDomain.Note.UNKNOWN}
        )
    if spammy_domains:
        resource.confirm_spam(save=True, domains=list(spammy_domains))

def _extract_domains(content):
    extracted_domains = set()
    for match in DOMAIN_REGEX.finditer(content):
        domain = match.group('domain')
        if not domain or domain in extracted_domains:
            continue

        protocol = match.group('protocol') or 'https://'
        www = match.group('www') or ''
        path = match.group('path') or ''
        constructed_url = f'{protocol}{www}{domain}{path}'

        try:
            response = requests.head(constructed_url)
        except (requests.exceptions.ConnectionError, requests.exceptions.InvalidURL):
            continue
        except requests.exceptions.RequestException:
            pass
        else:
            # Store the redirect location (to help catch link shorteners)
            if response.status_code in REDIRECT_CODES and 'location' in response.headers:
                redirect_match = DOMAIN_REGEX.match(response.headers['location'])
                if redirect_match:
                    domain = redirect_match.group('domain') or domain

        # Avoid returning a duplicate domain discovered via redirect
        if domain not in extracted_domains:
            extracted_domains.add(domain)
            yield domain


@celery_app.task()
def check_resource_with_spam_services(guid, content, author, author_email, request_kwargs):
    """
    Return statements used only for debugging and recording keeping
    """
    any_is_spam = False
    from osf.models import Guid
    guid = Guid.load(guid)
    if not guid:
        return f'{guid} not found'
    resource = guid.referent

    kwargs = dict(
        user_ip=request_kwargs.get('remote_addr'),
        user_agent=request_kwargs.get('user_agent'),
        referrer=request_kwargs.get('referer'),
        comment_content=content,
        comment_author=author,
        comment_author_email=author_email,
        content=content,
    )

    spam_clients = []
    if settings.AKISMET_ENABLED:
        spam_clients.append(AkismetClient())
    if settings.OOPSPAM_ENABLED:
        spam_clients.append(OOPSpamClient())

    for client in spam_clients:
        is_spam, details = client.check_content(**kwargs)
        if is_spam:
            any_is_spam = True
            if not resource.spam_data.get('who_flagged'):
                resource.spam_data['who_flagged'] = client.NAME
            elif resource.spam_data['who_flagged'] != client.NAME:
                resource.spam_data['who_flagged'] = 'both'

            if client.NAME == 'akismet':
                resource.spam_pro_tip = details
            if client.NAME == 'oopspam':
                resource.spam_data['oopspam_data'] = details

    if any_is_spam:
        resource.spam_data['headers'] = {
            'Remote-Addr': request_kwargs.get('remote_addr'),
            'User-Agent': request_kwargs.get('user_agent'),
            'Referer': request_kwargs.get('referer'),
        }
        resource.spam_data['content'] = content
        resource.spam_data['author'] = author
        resource.spam_data['author_email'] = author_email
        resource.flag_spam()

    resource.save()

    return f'{resource} is spam: {any_is_spam} {resource.spam_data.get("content")}'
