from osf.models.base import BaseModel, ObjectIDMixin
from osf.utils.datetime_aware_jsonfield import DateTimeAwareJSONField
from django.db import models
from osf.utils.fields import NonNaiveDateTimeField

class Session(ObjectIDMixin, BaseModel):
    data = DateTimeAwareJSONField(default=dict, blank=True)

    @property
    def is_authenticated(self):
        return 'auth_user_id' in self.data

    @property
    def is_external_first_login(self):
        return 'auth_user_external_first_login' in self.data
    
class UserSessions(BaseModel):
    class Meta:
        unique_together = ('user', 'session_key')
    user = models.ForeignKey('OSFUser', on_delete=models.CASCADE)
    session_key = models.CharField(max_length=255)
    expire_date = NonNaiveDateTimeField()
