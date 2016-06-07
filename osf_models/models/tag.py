from django.db import models

from .base import BaseModel


class Tag(BaseModel):
    _id = models.CharField(max_length=1024)
    lower = models.CharField(max_length=1024)
    system = models.BooleanField(default=False)

    def __unicode__(self):
        if self.system:
            return 'System Tag: {}'.format(self._id)
        return u'{}'.format(self._id)

    class Meta:
        unique_together = ('_id', 'system')
