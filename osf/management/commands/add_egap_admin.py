# -*- coding: utf-8 -*-
import logging

from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group
from waffle.models import Flag
from osf import features
from osf.models import OSFUser

logger = logging.getLogger(__name__)


def create_egap_admins_group(username):
    # `get_or_create` used here so command can be reused for new admins.
    flag, _ = Flag.objects.get_or_create(name=features.EGAP_ADMINS)
    group, _ = Group.objects.get_or_create(name=features.EGAP_ADMINS)  # Just using the same name for convenience
    flag.groups.add(group)
    user = OSFUser.objects.get(username=username)
    group.user_set.add(user)


class Command(BaseCommand):
    """
    This command adds a new waffle flag that only allows members of a django group named `EGAP_ADMINS` to hit it's
    active state.
    """
    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument(
            '-u',
            '--username',
            help='This should be the username of the EPAG administrator',
            required=True
        )

    def handle(self, *args, **options):
        username = options['username']
        create_egap_admins_group(username)
