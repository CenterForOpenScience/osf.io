from datetime import timedelta

from django.db import models
from django.utils import timezone

from api.base import settings

from .base import BaseModel
from osf.utils.fields import NonNaiveDateTimeField


class UserSessionMap(BaseModel):
    class Meta:
        unique_together = ('user', 'session_key')
    user = models.ForeignKey('OSFUser', on_delete=models.CASCADE)
    session_key = models.CharField(max_length=255)
    expire_date = NonNaiveDateTimeField()

    def save(self, *args, **kwargs):
        if self._state.adding and not self.expire_date:
            self.expire_date = timezone.now() + timedelta(seconds=settings.SESSION_COOKIE_AGE)
        super().save(*args, **kwargs)
