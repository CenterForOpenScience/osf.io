from django.db import models
from osf.utils.datetime_aware_jsonfield import DateTimeAwareJSONField
from .base import BaseModel, ObjectIDMixin


class CedarMetadataTemplate(ObjectIDMixin, BaseModel):
    title = models.CharField(max_length=255)
    template = DateTimeAwareJSONField(default=dict)
    active = models.BooleanField(default=True)
    template_version = models.PositiveIntegerField()

    class Meta:
        unique_together = ('title', 'template_version')

    def __unicode__(self):
        return f'({self.title}, version {self.tempate_version})'
