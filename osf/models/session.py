from django.db import models

from osf.models.base import BaseModel
from osf.utils.fields import NonNaiveDateTimeField


class UserSessionMap(BaseModel):
    class Meta:
        unique_together = ('user', 'session_key')
    user = models.ForeignKey('OSFUser', on_delete=models.CASCADE)
    session_key = models.CharField(max_length=255)
    expire_date = NonNaiveDateTimeField()
