# -*- coding: utf-8 -*-
import logging
import operator
from functools import reduce

from django.contrib.contenttypes.models import ContentType
from django.db.models import Q, OuterRef, Exists
from django.apps import apps
from django.core.management.base import BaseCommand
from osf.external.spam import tasks as spam_tasks
from osf.models import AbstractNode, DomainReference


logger = logging.getLogger(__name__)

DOMAIN_SEARCH_REGEX = r'(\w+\.\w+\w+\.\w+)|\w+\.\w+\w+'


def backfill_domain_references(model_name, dry_run=False, batch_size=None):
    model = apps.get_model(model_name)

    spam_fields = list(model.SPAM_CHECK_FIELDS)
    if issubclass(model, AbstractNode):
        spam_fields += ['wikis__versions__content']

    spam_queries = (
        Q(**{f'{field}__regex': DOMAIN_SEARCH_REGEX})
        for field in spam_fields
    )
    spam_content_query = reduce(operator.or_, spam_queries)

    spam_check_items = model.objects.annotate(
        exclude=Exists(
            DomainReference.objects.filter(
                referrer_content_type=ContentType.objects.get_for_model(model),
                referrer_object_id=OuterRef('id')
            )
        )
    ).filter(exclude=False).filter(spam_content_query)[:batch_size]

    spam_check_count = spam_check_items.count()
    logger.info(f'Queuing {spam_check_count} {model_name}s for domain extraction')
    for item in spam_check_items:
        logger.info(f'{item}, queued')
        spam_content = item._get_spam_content()
        if not dry_run:
            spam_tasks.check_resource_for_domains.apply_async(
                kwargs={'guid': item._id, 'content': spam_content}
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
            choices=['osf.Node', 'osf.Registration', 'osf.Preprint', 'osf.Comment', 'osf.User'],
            help='The name of the model to be searched for domains'
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
