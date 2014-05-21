# -*- coding: utf-8 -*-

import datetime

from modularodm import signals
from modularodm.fields import Field
from modularodm.validators import validate_datetime


DEFAULT_NOW = datetime.datetime.utcnow


def default_or_callable(value):
    if value is True:
        return DEFAULT_NOW
    if callable(value):
        return value
    raise ValueError('Value must be True or callable')


class DateTimeField(Field):

    validate = validate_datetime
    data_type = datetime.datetime
    mutable = True

    def __init__(self, *args, **kwargs):

        super(DateTimeField, self).__init__(*args, **kwargs)

        auto_now = kwargs.pop('auto_now', False)
        auto_now_add = kwargs.pop('auto_now_add', False)
        if auto_now and auto_now_add:
            raise ValueError('Cannot use auto_now and auto_now_add on the '
                             'same field.')

        #
        if (auto_now or auto_now_add) and 'editable' not in kwargs:
            self._editable = False
            self.lazy_default = False

        #
        if auto_now:
            self._auto_now = default_or_callable(auto_now)
        elif auto_now_add:
            self._default = default_or_callable(auto_now_add)

    def subscribe(self, sender=None):
        self.update_auto_now = signals.before_save.connect(
            self.update_auto_now,
            sender=sender,
        )

    def update_auto_now(self, cls, instance):
        if getattr(self, '_auto_now', None):
            self.data[instance] = self._auto_now()
