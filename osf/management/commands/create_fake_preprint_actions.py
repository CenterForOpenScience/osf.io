#!/usr/bin/env python
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import random
import logging
from faker import Faker

from django.core.management.base import BaseCommand

from osf.models import ReviewAction, PreprintService, OSFUser
from osf.utils.workflows import DefaultStates, DefaultTriggers

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """Add fake Actions to every preprint that doesn't already have one"""

    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument(
            'user',
            type=str,
            nargs='?',
            default=None,
            help='Guid for user to list as creator for all fake actions (default to arbitrary user)'
        )
        parser.add_argument(
            '--num-actions',
            action='store',
            type=int,
            default=10,
            help='Number of actions to create for each preprint which does not have one'
        )

    def handle(self, *args, **options):
        user_guid = options.get('user')
        num_actions = options.get('--num-actions')

        if user_guid is None:
            user = OSFUser.objects.first()
        else:
            user = OSFUser.objects.get(guids___id=user_guid)

        fake = Faker()
        triggers = [a.value for a in DefaultTriggers]
        states = [s.value for s in DefaultStates]
        for preprint in PreprintService.objects.filter(actions__isnull=True):
            for i in range(num_actions):
                action = ReviewAction(
                    target=preprint,
                    creator=user,
                    trigger=random.choice(triggers),
                    from_state=random.choice(states),
                    to_state=random.choice(states),
                    comment=fake.text(),
                )
                action.save()
