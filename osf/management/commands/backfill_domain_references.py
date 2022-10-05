# -*- coding: utf-8 -*-
import re
import logging
import operator
from functools import reduce

from django.db.models import Q
from django.core.management.base import BaseCommand
from osf.external.spam.tasks import check_resource_for_domains
from osf.models import Preprint, OSFUser, Node, Comment, Registration
from addons.wiki.models import WikiVersion

logger = logging.getLogger(__name__)

DOMAIN_MATCH_REGEX = re.compile(r'(?P<protocol>\w+://)?(?P<www>www\.)?(?P<domain>[\w-]+\.\w+)(?P<path>/\w*)?')
DOMAIN_SEARCH_REGEX = r'(http://[^ \'}\[\]\~\(\)\/]+|https://[^ \'}\[\]\~\(\)\/]+)'


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
        for item in queryset:
            if isinstance(item, WikiVersion):  # Wiki version has no `spam_status` this will work via the user status
                guid = item.user._id
            else:
                guid = item._id

            spam_content = item._get_spam_content(saved_fields=list(item.SPAM_CHECK_FIELDS))
            if not dry_run:
                check_resource_for_domains.apply_async(
                    kwargs=dict(
                        guid=guid,
                        content=spam_content,
                    )
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
