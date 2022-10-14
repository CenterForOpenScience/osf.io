# -*- coding: utf-8 -*-
import re
import logging
import operator
from functools import reduce

from django.db.models import Q
from django.core.management.base import BaseCommand
from osf.external.spam.tasks import migrate_check_resource_for_domains
from osf.models import Preprint, OSFUser, Node, Comment, Registration
from addons.wiki.models import WikiVersion
from django_celery_results.models import TaskResult


logger = logging.getLogger(__name__)

DOMAIN_MATCH_REGEX = re.compile(r'(?P<protocol>\w+://)?(?P<www>www\.)?(?P<domain>[\w-]+\.\w+)(?P<path>/\w*)?')
DOMAIN_SEARCH_REGEX = r'(http://[^ \'}\[\]\~\(\)\/]+|https://[^ \'}\[\]\~\(\)\/]+)'


def backfill_domain_references(dry_run=False, batch_size=None):
    model_list = [Preprint, OSFUser, Node, Comment, Registration, WikiVersion]

    completed_tasks = TaskResult.objects.filter(
        result__regex=r'check_resource_for_domains:[a-zA-Z0-9_.-]{5,}'
    )

    completed_tasks_guids = [task.result.split(':')[1].rstrip('"') for task in completed_tasks]
    logger.info(f'found {len(completed_tasks_guids)} completed tasks')

    queries = []
    for model in model_list:
        query = reduce(
            operator.or_,
            (Q(**{f'{field}__regex': DOMAIN_SEARCH_REGEX}) for field in list(model.SPAM_CHECK_FIELDS))
        )
        queries.append(model.objects.filter(query))

    for queryset in queries:
        if queryset.query.model == WikiVersion:  # Wiki version has no `spam_status` this will work via the user status
            queryset = queryset.exclude(user__guids___id__in=completed_tasks_guids)
        else:
            queryset = queryset.exclude(guids___id__in=completed_tasks_guids)

        logger.info(f'{queryset.count()} of class: {queryset.query.model} to check')

        for item in queryset:
            if isinstance(item, WikiVersion):  # Wiki version has no `spam_status` this will work via the user status
                guid = item.user._id
            else:
                guid = item._id

            spam_content = item._get_spam_content()
            if not dry_run:
                migrate_check_resource_for_domains.apply_async(
                    kwargs=dict(
                        guid=guid,
                        content=spam_content,
                    )
                )
                logger.info(f'{item}, queued')


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
