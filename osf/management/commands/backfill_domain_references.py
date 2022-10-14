# -*- coding: utf-8 -*-
import re
import logging
import datetime
import operator
from functools import reduce

from django.db.models import Q
from django.apps import apps
from django.core.management.base import BaseCommand
from osf.external.spam.tasks import check_resource_for_domains
from addons.wiki.models import WikiVersion


logger = logging.getLogger(__name__)

DOMAIN_MATCH_REGEX = re.compile(r'(?P<protocol>\w+://)?(?P<www>www\.)?(?P<domain>[\w-]+\.\w+)(?P<path>/\w*)?')
DOMAIN_SEARCH_REGEX = r'(http://[^ \'}\[\]\~\(\)\/]+|https://[^ \'}\[\]\~\(\)\/]+)'


def spawn_tasks_for_domain_references_backfill(model, query, get_guid, batch_size=None, dry_run=False):
    for item in model.objects.filter(query)[:batch_size]:
        spam_content = item._get_spam_content()
        if not dry_run:
            check_resource_for_domains.apply_async(
                kwargs=dict(
                    guid=get_guid(item),
                    content=spam_content,
                )
            )
            logger.info(f'{item}, queued')


def backfill_domain_references(date_modified, model_name, dry_run=False, batch_size=None):
    model = apps.get_model(model_name)
    query = reduce(
        operator.or_,
        (Q(**{f'{field}__regex': DOMAIN_SEARCH_REGEX}) for field in list(model.SPAM_CHECK_FIELDS))
    ) & Q(modified__lte=date_modified)

    if model == WikiVersion:
        get_guid = lambda item: item.wiki_page.node._id
    else:
        get_guid = lambda item: item._id

    spawn_tasks_for_domain_references_backfill(
        model,
        query,
        get_guid=get_guid,
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
            '--modified_date',
            '-m',
            required=True,
            type=lambda s: datetime.datetime.strptime(s, '%Y-%m-%d %H:%M:%S.%f'),
        )
        parser.add_argument(
            '--model_name',
            type=str,
            required=True,
            help='The name of the model to be searched for domains',
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
        date_modified = options.get('date_modified', None)
        model_name = options.get('model_name', None)
        batch_size = options.get('batch_size', None)
        backfill_domain_references(date_modified, model_name, dry_run, batch_size)
