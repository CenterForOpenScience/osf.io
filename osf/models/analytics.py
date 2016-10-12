import logging

from dateutil import parser
from django.db import models, transaction, connection
from django.utils import timezone

from osf.models.base import BaseModel
from osf.utils.datetime_aware_jsonfield import DateTimeAwareJSONField

logger = logging.getLogger(__name__)


class UserActivityCounter(BaseModel):
    _id = models.CharField(max_length=255, null=False, blank=False, db_index=True,
                           unique=True)
    action = DateTimeAwareJSONField(default=dict)
    date = DateTimeAwareJSONField(default=dict)
    total = models.PositiveIntegerField(default=0)

    @classmethod
    def get_total_activity_count(cls, user_id):
        try:
            return cls.objects.get(_id=user_id).total
        except cls.DoesNotExist:
            return 0

    @classmethod
    def increment(cls, user_id, action, date_string):
        date = parser.parse(date_string).strftime('%Y/%m/%d')
        with transaction.atomic():
            # select_for_update locks the row but only inside a transaction
            uac, created = cls.objects.select_for_update().get_or_create(_id=user_id)
            if uac.total > 0:
                uac.total += 1
            else:
                uac.total = 1
            if action in uac.action:
                uac.action[action]['total'] += 1
                if date in uac.action[action]['date']:
                    uac.action[action]['date'][date] += 1
                else:
                    uac.action[action]['date'][date] = 1
            else:
                uac.action[action] = dict(total=1, date={date: 1})
            if date in uac.date:
                uac.date[date]['total'] += 1
            else:
                uac.date[date] = dict(total=1)
            uac.save()
        return True


class PageCounter(BaseModel):
    _id = models.CharField(max_length=255, null=False, blank=False, db_index=True,
                           unique=True)
    date = DateTimeAwareJSONField(default=dict)
    total = models.PositiveIntegerField(default=1)
    unique = models.PositiveIntegerField(default=1)

    # @classmethod
    # def update_counter(cls, page, node_info):
    #     date = timezone.now()
    #     date_string = date.strftime('%Y/%m/%d')
    #     page = page.replace(
    #         '.', '_'
    #     ).replace(
    #         '$', '_'
    #     )

