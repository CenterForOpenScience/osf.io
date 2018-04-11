# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from enum import unique

from osf.utils.workflows import ChoiceEnum, DefaultStates


@unique
class Workflows(ChoiceEnum):
    NONE = None
    PRE_MODERATION = 'pre-moderation'
    POST_MODERATION = 'post-moderation'

PUBLIC_STATES = {
    Workflows.NONE.value: (
        DefaultStates.INITIAL.value,
        DefaultStates.PENDING.value,
        DefaultStates.ACCEPTED.value,
        DefaultStates.REJECTED.value,
    ),
    Workflows.PRE_MODERATION.value: (
        DefaultStates.ACCEPTED.value,
    ),
    Workflows.POST_MODERATION.value: (
        DefaultStates.PENDING.value,
        DefaultStates.ACCEPTED.value,
    )
}
