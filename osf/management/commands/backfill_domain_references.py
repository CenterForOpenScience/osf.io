# -*- coding: utf-8 -*-
import re
import logging
import operator
from functools import reduce

from django.db.models import Q, OuterRef, Exists
from django.apps import apps
from django.core.management.base import BaseCommand
from osf.external.spam.tasks import check_resource_for_domains
from osf.models import DomainReference, AbstractNode
from addons.wiki.models import WikiVersion


logger = logging.getLogger(__name__)

DOMAIN_MATCH_REGEX = re.compile(r'(?P<protocol>\w+://)?(?P<www>www\.)?(?P<domain>[\w-]+\.\w+)(?P<path>/\w*)?')
DOMAIN_SEARCH_REGEX = r'(http://[^ \'}\[\]\~\(\)\/]+|https://[^ \'}\[\]\~\(\)\/]+)'
from django.contrib.contenttypes.models import ContentType


def spawn_tasks_for_domain_references_backfill(model, query, get_guid, exclusion_subquery=None, batch_size=None, dry_run=False):
    items = model.objects.filter(query).annotate(
        exclude=exclusion_subquery
    ).filter(exclude=True)[:batch_size]

    for item in items:
        spam_content = item._get_spam_content()
        if not dry_run:
            check_resource_for_domains.apply_async(
                kwargs=dict(
                    guid=get_guid(item),
                    content=spam_content,
                )
            )
            logger.info(f'{item}, queued')


def backfill_domain_references(model_name, dry_run=False, batch_size=None):
    model = apps.get_model(model_name)
    query = reduce(
        operator.or_,
        (Q(**{f'{field}__regex': DOMAIN_SEARCH_REGEX}) for field in list(model.SPAM_CHECK_FIELDS))
    )

    if model == WikiVersion:
        get_guid = lambda item: item.wiki_page.node._id
        node_ids = model.objects.filter(query).values_list('wiki_page__node__id', flat=True)
        exclusion_subquery = ~Exists(
            DomainReference.objects.filter(
                referrer_content_type=ContentType.objects.get_for_model(AbstractNode),
                referrer_object_id__in=list(node_ids)
            )
        )

    else:
        get_guid = lambda item: item._id
        exclusion_subquery = ~Exists(
            DomainReference.objects.filter(
                referrer_content_type=ContentType.objects.get_for_model(model),
                referrer_object_id=OuterRef('id')
            )
        )

    spawn_tasks_for_domain_references_backfill(
        model,
        query,
        get_guid=get_guid,
        exclusion_subquery=exclusion_subquery,
        batch_size=batch_size,
        dry_run=dry_run
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
        parser.add_argument(
            '--model_name',
            type=str,
            required=True,
            help='The name of the model to be searched for domains, '
                 'remember WikiVersions app label name is addons_wiki.WikiVersion',
        )
        parser.add_argument(
            '--batch_size',
            '-b',
            type=int,
            required=False,
            help='The number of instances of the model to be searched for domains',
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', None)
        model_name = options.get('model_name', None)
        batch_size = options.get('batch_size', None)
        backfill_domain_references(model_name, dry_run, batch_size)
