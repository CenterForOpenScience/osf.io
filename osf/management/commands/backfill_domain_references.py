# -*- coding: utf-8 -*-
import re
import logging
import operator
from functools import reduce

from django.apps import apps
from django.db.models import Q
from django.core.management.base import BaseCommand
from framework.celery_tasks import app as celery_app
from osf.models import NotableDomain, DomainReference
from django.contrib.contenttypes.models import ContentType
from osf.models import Preprint, OSFUser, Node, Comment, Registration
from addons.wiki.models import WikiVersion

logger = logging.getLogger(__name__)

DOMAIN_MATCH_REGEX = re.compile(r'(?P<protocol>\w+://)?(?P<www>www\.)?(?P<domain>[\w-]+\.\w+)(?P<path>/\w*)?')
DOMAIN_SEARCH_REGEX = r'(http://[^ \'}\[\]\~\(\)\/]+|https://[^ \'}\[\]\~\(\)\/]+)'


@celery_app.task()
def create_notable_domain_with_reference(domain, resource_id, resource_content_type_pk):
    domain, created = NotableDomain.objects.get_or_create(
        domain=domain,
        defaults={'note': NotableDomain.Note.UNKNOWN}
    )
    DomainReference.objects.get_or_create(
        domain=domain,
        referrer_object_id=resource_id,
        referrer_content_type_id=resource_content_type_pk
    )

    if created:
        logger.info(f'Creating NotableDomain {domain}')


def backfill_domain_references(dry_run=False):
    model_list = [Preprint, OSFUser, Node, Comment, Registration, WikiVersion]

    queries = []
    for model in model_list:
        query = reduce(
            operator.or_,
            (Q(**{f'{field}__regex': DOMAIN_SEARCH_REGEX}) for field in list(model.SPAM_CHECK_FIELDS))
        )
        queries.append(model.objects.filter(query))

    for queryset in queries:
        for resource_data in queryset.values(*list(queryset.query.model.SPAM_CHECK_FIELDS), 'pk'):
            domains = list({match.group('domain') for match in re.finditer(DOMAIN_MATCH_REGEX, str(resource_data))})
            for domain in domains:
                if not dry_run:
                    create_notable_domain_with_reference.apply_async(
                        kwargs={
                            'domain': domain,
                            'resource_id': resource_data['pk'],
                            'resource_content_type_pk': ContentType.objects.get_for_model(queryset.query.model).id,
                        }
                    )


class Command(BaseCommand):
    help = '''Management command that finds domains in fields for that models `SPAM_CHECK_FIELDS` '''

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry_run',
            type=bool,
            default=False,
            help='Run queries but do not create instances',
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', None)
        backfill_domain_references(dry_run)
