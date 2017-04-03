from django.utils import timezone
from osf.models.base import BaseModel, ObjectIDMixin
from osf.utils.datetime_aware_jsonfield import DateTimeAwareJSONField
from osf.utils.fields import NonNaiveDateTimeField


class Session(ObjectIDMixin, BaseModel):
    # TODO DELETE ME POST MIGRATION
    modm_model_path = 'framework.sessions.model.Session'
    modm_query = None
    migration_page_size = 30000
    # /TODO DELETE ME POST MIGRATION
    date_created = NonNaiveDateTimeField(default=timezone.now)
    date_modified = NonNaiveDateTimeField(default=timezone.now)  # auto_now=True)
    data = DateTimeAwareJSONField(default=dict, blank=True)

    @property
    def is_authenticated(self):
        return 'auth_user_id' in self.data

    @property
    def is_external_first_login(self):
        return 'auth_user_external_first_login' in self.data
