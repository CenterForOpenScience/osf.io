from framework.celery_tasks import app as celery_app
from django.db import transaction

@celery_app.task()
def reclassify_domain_references(notable_domain_id):
    from osf.models.notable_domain import DomainReference, NotableDomain
    domain = NotableDomain.load(notable_domain_id)
    references = DomainReference.objects.filter(domain=domain)
    with transaction.atomic():
        for item in references:
            if domain.note == NotableDomain.Note.EXCLUDE_FROM_ACCOUNT_CREATION_AND_CONTENT:
                item.referrer.confirm_spam(save=True)
                item.is_triaged = True
            item.save()
