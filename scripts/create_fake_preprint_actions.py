#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Add fake Actions to every preprint that doesn't already have one"""
from __future__ import unicode_literals

import random
import sys
import logging
from website.app import setup_django
from faker import Faker

setup_django()
from reviews import workflow
from osf.models import Action, PreprintService, OSFUser

def main():
    user = OSFUser.objects.first()
    fake = Faker()
    triggers = [a.value for a in workflow.Triggers]
    states = [s.value for s in workflow.States]
    for preprint in PreprintService.objects.filter(actions__isnull=True):
        for i in range(10):
            action = Action(
                target=preprint,
                creator=user,
                trigger=random.choice(triggers),
                from_state=random.choice(states),
                to_state=random.choice(states),
                comment=fake.text(),
            )
            action.save()

if __name__ == '__main__':
    main()
