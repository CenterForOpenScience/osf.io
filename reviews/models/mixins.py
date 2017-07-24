# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from transitions import Machine

from django.db import models

from reviews.workflow import States
from reviews.workflow import Workflows
from reviews.workflow import TRANSITIONS


class ReviewProviderMixin(models.Model):
    """A reviewed/moderated collection of objects.
    """

    reviews_workflow = models.CharField(max_length=15, choices=Workflows.choices(), default=Workflows.PRE_MODERATION.value)
    reviews_comments_private = models.BooleanField(default=True)
    reviews_comments_anonymous = models.BooleanField(default=True)

    class Meta:
        abstract = True


class ReviewableMixin(models.Model):
    """Something that may be included in a reviewed collection and is subject to a reviews workflow
    """

    reviews_state = models.CharField(max_length=15, db_index=True, choices=States.choices(), default=States.PENDING.value)

    def __init__(self, *args, **kwargs):
        super(ReviewableMixin, self).__init__(*args, **kwargs)

        self.__machine = ReviewsMachine(self)

    def reviews_accept(self, *args, **kwargs):
        return self.__machine.accept(*args, **kwargs)

    def reviews_reject(self, *args, **kwargs):
        return self.__machine.reject(*args, **kwargs)

    class Meta:
        abstract = True


class ReviewsMachine(Machine):

    def __init__(self, reviewable, state_attr='reviews_state'):
        self.__reviewable = reviewable
        self.__state_attr = state_attr

        super(ReviewsMachine, self).__init__(
            states=[s.value for s in States],
            transitions=TRANSITIONS,
            initial=self.state,
            send_event=True,
            before_state_change='check_permission',
            finalize_event='save_changes',
        )

    @property
    def state(self):
        return getattr(self.__reviewable, self.__state_attr)

    @state.setter
    def state(self, value):
        setattr(self.__reviewable, self.__state_attr, value)

    def notify_accepted(self, event):
        # TODO email submitter
        pass

    def notify_rejected(self, event):
        # TODO email submitter
        pass

    def check_permission(self, event):
        # TODO raise if user does not have permission (MOD-22)
        pass

    def save_changes(self, event):
        # TODO save a new review log, with comment from kwargs (MOD-23)
        if self.state != event.state:
            self.__reviewable.save()
