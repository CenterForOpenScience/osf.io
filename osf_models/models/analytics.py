from dateutil import parser
from django.db import models
from osf_models.models.base import BaseModel
from osf_models.utils.datetime_aware_jsonfield import DateTimeAwareJSONField


class UserActivityCounter(BaseModel):
    _id = models.CharField(max_length=255, null=False, blank=False, db_index=True,
                           unique=True)
    action = DateTimeAwareJSONField(default=dict)
    date = DateTimeAwareJSONField(default=dict)
    total = models.PositiveIntegerField()

    @classmethod
    def increment(self, user_id, action, date_string):
        date = parser.parse(date_string).strftime('%Y/%m/%d')
        date = date


class PageCounter(BaseModel):
    _id = models.CharField(max_length=255, null=False, blank=False, db_index=True,
                           unique=True)
    date = DateTimeAwareJSONField(default=dict)
    total = models.PositiveIntegerField()
    unique = models.PositiveIntegerField()
