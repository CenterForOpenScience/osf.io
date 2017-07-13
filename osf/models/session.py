from osf.models.base import BaseModel, ObjectIDMixin
from osf.utils.datetime_aware_jsonfield import DateTimeAwareJSONField


class Session(ObjectIDMixin, BaseModel):
    data = DateTimeAwareJSONField(default=dict, blank=True)

    @property
    def is_authenticated(self):
        return 'auth_user_id' in self.data

    @property
    def is_external_first_login(self):
        return 'auth_user_external_first_login' in self.data
