from django.db import models

from osf_models.utils.datetime_aware_jsonfield import DateTimeAwareJSONField
from osf_models.models.base import BaseModel, ObjectIDMixin


class Session(ObjectIDMixin, BaseModel):
    date_created = models.DateTimeField(auto_now_add=True)
    date_modified = models.DateTimeField(auto_now=True)
    data = DateTimeAwareJSONField(default=dict, blank=True)

    @property
    def is_authenticated(self):
        return 'auth_user_id' in self.data
