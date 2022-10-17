from multiprocessing.sharedctypes import Value
import re
import logging
from framework.celery_tasks import app as celery_app
from django.contrib.contenttypes.models import ContentType
from django.db import transaction

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

DOMAIN_REGEX = re.compile(r'(?P<protocol>\w+://)?(?P<www>www\.)?(?P<domain>[\w-]+\.\w+)(?P<path>/\w*)?')

@celery_app.task()
def reclassify_domain_references(notable_domain_id):
    from osf.models.notable_domain import DomainReference, NotableDomain
    from osf.models.spam import SpamStatus
    domain = NotableDomain.load(notable_domain_id)
    references = DomainReference.objects.filter(domain=domain)
    with transaction.atomic():
        for item in references:
            item.is_triaged = domain.note != NotableDomain.Note.UNKNOWN
            if domain.note == NotableDomain.Note.EXCLUDE_FROM_ACCOUNT_CREATION_AND_CONTENT:
                item.referrer.confirm_spam(save=False, domains=[domain.domain])
            elif domain.note == NotableDomain.Note.UNKNOWN or domain.note == NotableDomain.Note.IGNORED:
                if item.referrer.spam_status == SpamStatus.SPAM:
                    try:
                        item.referrer.spam_data['domains'].remove(domain.domain)
                    except (KeyError, AttributeError, ValueError) as error:
                        logger.info(error)
                    if len(item.referrer.spam_data['domains']) == 0:
                        item.referrer.unspam(save=False)
            item.save()
            item.referrer.save()

@celery_app.task()
def check_resource_for_domains(guid, content):
    from osf.models import Guid, NotableDomain, DomainReference
    resource = Guid.load(guid).referent
    domains = {match.group('domain') for match in re.finditer(DOMAIN_REGEX, content)}
    spammy_domains = []
    referrer_content_type = ContentType.objects.get_for_model(resource)
    for domain in domains:
        domain, _ = NotableDomain.objects.get_or_create(domain=domain)
        if domain.note == NotableDomain.Note.EXCLUDE_FROM_ACCOUNT_CREATION_AND_CONTENT:
            spammy_domains.append(domain.domain)
        DomainReference.objects.get_or_create(
            domain=domain,
            referrer_object_id=resource.id,
            referrer_content_type=referrer_content_type,
            defaults={'is_triaged': domain.note != NotableDomain.Note.UNKNOWN}
        )
    if spammy_domains:
        resource.confirm_spam(save=True, domains=list(spammy_domains))
