# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from enum import Enum
from enum import unique

@unique
class Workflows(Enum):
    PRE_MODERATION = 'pre-moderation'
    POST_MODERATION = 'post-moderation'

    @classmethod
    def choices(cls):
        return tuple((w.value, w.value.title()) for w in cls)

@unique
class States(Enum):
    PENDING = 'pending'
    ACCEPTED = 'accepted'
    REJECTED = 'rejected'

    @classmethod
    def choices(cls):
        return tuple((s.value, s.value.title()) for s in cls)

TRANSITIONS = [
    {
        'trigger': 'accept',
        'source': [States.PENDING.value, States.REJECTED.value],
        'dest': States.ACCEPTED.value,
        'after': ['notify_accepted'],
    },
    {
        'trigger': 'reject',
        'source': [States.PENDING.value, States.ACCEPTED.value],
        'dest': States.REJECTED.value,
        'after': ['notify_rejected'],
    },
]
