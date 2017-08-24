#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Add fake ReviewLogs to every preprint that doesn't have one"""
from __future__ import unicode_literals

import random
import sys
import logging
from website.app import setup_django
from faker import Faker

setup_django()
from reviews import workflow
from reviews.models import ReviewLog
from osf.models import PreprintService, OSFUser

def main():
    user = OSFUser.objects.first()
    fake = Faker()
    actions = [a.value for a in workflow.Actions]
    states = [s.value for s in workflow.States]
    for preprint in PreprintService.objects.filter(review_logs__isnull=True):
        for i in range(10):
            log = ReviewLog(
                reviewable=preprint,
                creator=user,
                action=random.choice(actions),
                from_state=random.choice(states),
                to_state=random.choice(states),
                comment=fake.text(),
            )
            log.save()

if __name__ == '__main__':
    main()
