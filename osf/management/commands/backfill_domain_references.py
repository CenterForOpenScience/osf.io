import logging
import operator
from functools import reduce


from django.apps import apps
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand
from django.db.models import Exists, OuterRef, Q, Value

from addons.wiki.models import WikiVersion
from osf.external.spam import tasks as spam_tasks
from osf.models import AbstractNode, DomainReference
from website.settings import DO_NOT_INDEX_LIST


logger = logging.getLogger(__name__)

DOMAIN_SEARCH_REGEX = r'(\w+\.\w+\w+\.\w+)|\w+\.\w+\w+'


def backfill_domain_references(model_name, dry_run=False, batch_size=None, ignore_spam=False):
    model = apps.get_model(model_name)

    spam_fields = list(model.SPAM_CHECK_FIELDS)
    if issubclass(model, AbstractNode):
        has_spam_wikis_subquery = Exists(
            WikiVersion.objects.filter(
                wiki_page__node__id=OuterRef('id'),
                content__regex=DOMAIN_SEARCH_REGEX
            )
        )
        qa_queries = (
            Q(**{'title__contains': qa_substr})
            for qa_substr in DO_NOT_INDEX_LIST['titles']
        )
        is_qa_node = reduce(operator.or_, qa_queries)
    else:
        has_spam_wikis_subquery = Value(False)
        is_qa_node = Q()
    if ignore_spam:
        ignore_q = Q(spam_status__in=[1, 2])
    else:
        ignore_q = Q()

    spam_queries = (
        Q(**{f'{field}__regex': DOMAIN_SEARCH_REGEX})
        for field in spam_fields
    )
    has_spam_content = reduce(operator.or_, spam_queries) | Q(has_spam_wikis=True)

    spam_check_items = model.objects.annotate(
        exclude=Exists(
            DomainReference.objects.filter(
                referrer_content_type=ContentType.objects.get_for_model(model),
                referrer_object_id=OuterRef('id')
            )
        ),
        has_spam_wikis=has_spam_wikis_subquery
    ).filter(exclude=False).filter(has_spam_content).exclude(is_qa_node).exclude(ignore_q).order_by('?')[:batch_size]

    spam_check_count = spam_check_items.count()
    logger.info(f'Queuing {spam_check_count} {model_name}s for domain extraction')
    for item in spam_check_items:
        logger.info(f'{item}, queued')
        spam_content = item._get_spam_content(include_tags=False)
        if not dry_run:
            spam_tasks.check_resource_for_domains_async.apply_async(
                kwargs={'guid': item._id, 'content': spam_content}
            )
    return spam_check_count


class Command(BaseCommand):
    help = '''Management command that finds domains in fields for that models `SPAM_CHECK_FIELDS` '''

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry_run',
            action='store_true',
            default=False,
            help='Run queries but do not create instances',
        )
        parser.add_argument(
            '--model_name',
            type=str,
            required=True,
            choices=['osf.Node', 'osf.Registration', 'osf.Preprint', 'osf.Comment', 'osf.OSFUser'],
            help='The name of the model to be searched for domains'
        )
        parser.add_argument(
            '--batch_size',
            '-b',
            type=int,
            required=False,
            help='The number of instances of the model to be searched for domains',
        )
        parser.add_argument(
            '--ignore_known_spam',
            '-i',
            action='store_true',
            default=False,
            help='Ignore items already flagged or marked spam'
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run', None)
        model_name = options.get('model_name', None)
        batch_size = options.get('batch_size', None)
        ignore = options.get('ignore_known_spam', None)
        backfill_domain_references(model_name, dry_run, batch_size, ignore)
