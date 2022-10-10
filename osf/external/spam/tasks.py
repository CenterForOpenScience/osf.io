import re
from framework.celery_tasks import app as celery_app
from django.contrib.contenttypes.models import ContentType
from django.db import transaction

DOMAIN_REGEX = re.compile(r'(?P<protocol>\w+://)?(?P<www>www\.)?(?P<domain>[\w-]+\.\w+)(?P<path>/\w*)?')

@celery_app.task()
def reclassify_domain_references(notable_domain_id):
    from osf.models.notable_domain import DomainReference, NotableDomain
    from osf.models.spam import SpamStatus
    spammy_domains_set = set(NotableDomain.objects.filter(note=NotableDomain.Note.EXCLUDE_FROM_ACCOUNT_CREATION_AND_CONTENT).values_list('domain', flat=True))
    domain = NotableDomain.load(notable_domain_id)
    references = DomainReference.objects.filter(domain=domain)
    with transaction.atomic():
        for item in references:
            item.is_triaged = domain.note != NotableDomain.Note.UNKNOWN
            if domain.note == NotableDomain.Note.EXCLUDE_FROM_ACCOUNT_CREATION_AND_CONTENT:
                item.referrer.confirm_spam(save=False, domains=[domain.domain])
            elif domain.note == NotableDomain.Note.UNKNOWN or domain.note == NotableDomain.Note.IGNORED:
                if item.referrer.spam_status == SpamStatus.SPAM:
                    item.referrer.spam_data['domains'].remove(domain.domain)
                    if set(item.referrer.spam_data['domains']).isdisjoint(spammy_domains_set):
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
    mark_spam = False
    for domain in domains:
        domain, _ = NotableDomain.objects.get_or_create(domain=domain)
        if domain.note == NotableDomain.Note.EXCLUDE_FROM_ACCOUNT_CREATION_AND_CONTENT:
            spammy_domains.append(domain.domain)
            mark_spam = True
        DomainReference.objects.get_or_create(
            domain=domain,
            referrer_object_id=resource.id,
            referrer_content_type=referrer_content_type,
            defaults={'is_triaged': domain.note != NotableDomain.Note.UNKNOWN}
        )
    if mark_spam:
        resource.confirm_spam(save=True, domains=list(spammy_domains))
