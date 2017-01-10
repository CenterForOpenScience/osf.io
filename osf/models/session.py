from django.utils import timezone

from osf.utils.datetime_aware_jsonfield import DateTimeAwareJSONField
from osf.models.base import BaseModel, ObjectIDMixin
from osf.utils.fields import NonNaiveDatetimeField


class Session(ObjectIDMixin, BaseModel):
    # TODO DELETE ME POST MIGRATION
    modm_model_path = 'framework.sessions.model.Session'
    modm_query = None
    migration_page_size = 30000
    # /TODO DELETE ME POST MIGRATION
    date_created = NonNaiveDatetimeField(default=timezone.now)
    date_modified = NonNaiveDatetimeField(auto_now=True)
    data = DateTimeAwareJSONField(default=dict, blank=True)

    @property
    def is_authenticated(self):
        return 'auth_user_id' in self.data

    @property
    def is_external_first_login(self):
        return 'auth_user_external_first_login' in self.data
