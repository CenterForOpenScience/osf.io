import re
import logging
import requests
from framework.celery_tasks import app as celery_app
from django.contrib.contenttypes.models import ContentType
from django.db import transaction

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


DOMAIN_REGEX = re.compile(r'\W*(?P<protocol>\w+://)?(?P<www>www\.)?(?P<domain>([\w-]+\.)+\w+)(?P<path>/\w*)?\W*')
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
    resource = Guid.load(guid).referent
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
        constructed_url = f'{protocol}{www}{domain}'

        try:
            response = requests.head(constructed_url)
        except (requests.exceptions.ConnectionError, requests.exceptions.InvalidURL):
            continue
        except requests.exceptions.RequestException:
            pass
        else:
            # Store the redirect location (to help catch link shorteners)
            if response.status_code in REDIRECT_CODES and 'location' in response.headers:
                domain = DOMAIN_REGEX.match(response.headers['location']).group('domain')

        # Avoid returning a duplicate domain discovered via redirect
        if domain not in extracted_domains:
            extracted_domains.add(domain)
            yield domain
