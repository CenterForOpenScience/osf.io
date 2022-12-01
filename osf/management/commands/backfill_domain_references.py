# -*- coding: utf-8 -*-
import re
import logging
import operator
from functools import reduce

from django.db.models import Q, OuterRef, Exists
from django.apps import apps
from django.core.management.base import BaseCommand
from osf.external.spam.tasks import check_resource_for_domains
from osf.models import DomainReference


logger = logging.getLogger(__name__)

DOMAIN_MATCH_REGEX = re.compile(r'(?P<protocol>\w+://)?(?P<www>www\.)?(?P<domain>[\w-]+\.\w+)(?P<path>/\w*)?')
DOMAIN_SEARCH_REGEX = r'(\w+\.\w+\w+\.\w+)|\w+\.\w+\w+'
from django.contrib.contenttypes.models import ContentType
from osf.models import Node


def spawn_tasks_for_domain_references_backfill(model, query, additional_spam_fields=None, batch_size=None, dry_run=False):
    items = model.objects.filter(query).annotate(
        exclude=~Exists(
            DomainReference.objects.filter(
                referrer_content_type=ContentType.objects.get_for_model(model),
                referrer_object_id=OuterRef('id')
            )
        )
    ).filter(exclude=True)[:batch_size]

    for item in items:
        spam_content = item._get_spam_content(additional_spam_fields)

        if not dry_run:
            check_resource_for_domains.apply_async(
                kwargs=dict(
                    guid=item._id,
                    content=spam_content,
                )
            )
            logger.info(f'{item}, queued')


def backfill_domain_references(model_name, dry_run=False, batch_size=None):
    model = apps.get_model(model_name)
    spam_fields = None

    if model == Node:
        spam_fields = list(Node.SPAM_CHECK_FIELDS) + ['wikis__versions__content']
        search_fields = list(model.SPAM_CHECK_FIELDS) + ['wikis__versions__content']
    else:
        search_fields = list(model.SPAM_CHECK_FIELDS)

    spam_queries = (Q(**{f'{field}__regex': DOMAIN_SEARCH_REGEX}) for field in search_fields)
    query = reduce(operator.or_, spam_queries)

    spawn_tasks_for_domain_references_backfill(
        model,
        query,
        additional_spam_fields=spam_fields,
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
