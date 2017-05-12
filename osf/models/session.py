from django.contrib.postgres.fields import JSONField

from osf.models.base import BaseModel, ObjectIDMixin
from osf.utils.datetime_aware_jsonfield import DateTimeAwareJSONEncoder
from osf.utils.fields import NonNaiveDateTimeField


class Session(ObjectIDMixin, BaseModel):
    date_created = NonNaiveDateTimeField(auto_now_add=True)
    date_modified = NonNaiveDateTimeField(auto_now=True)
    data = JSONField(encoder=DateTimeAwareJSONEncoder, default=dict, blank=True)

    @property
    def is_authenticated(self):
        return 'auth_user_id' in self.data

    @property
    def is_external_first_login(self):
        return 'auth_user_external_first_login' in self.data
