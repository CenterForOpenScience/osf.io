# -*- coding: utf-8 -*-
from django.db import models
from django.core.exceptions import ValidationError

from website.util import api_v2_url

from osf.models.base import BaseModel, ObjectIDMixin
from osf.models.preprint_provider import PreprintProvider
from osf.models.preprint_service import PreprintService
from osf.models.validators import validate_subject_hierarchy_length, validate_subject_provider_mapping
from osf.utils.caching import cached_property


class Subject(ObjectIDMixin, BaseModel):
    """A subject discipline that may be attached to a preprint."""
    modm_model_path = 'website.project.taxonomies.Subject'
    modm_query = None

    text = models.CharField(null=False, max_length=256, unique=True)  # max length on prod: 73
    parent = models.ForeignKey('self', related_name='children', null=True, blank=True, on_delete=models.SET_NULL)
    bepress_subject = models.ForeignKey('self', related_name='aliases', null=True, blank=True, on_delete=models.deletion.CASCADE)
    provider = models.ForeignKey(PreprintProvider, related_name='subjects', on_delete=models.deletion.CASCADE)

    def __unicode__(self):
        return '{} with id {}'.format(self.text, self.id)

    @property
    def absolute_api_v2_url(self):
        return api_v2_url('taxonomies/{}/'.format(self._id))

    @property
    def child_count(self):
        """For v1 compat."""
        return self.children.count()

    def get_absolute_url(self):
        return self.absolute_api_v2_url

    @cached_property
    def hierarchy(self):
        if self.parent:
            return self.parent.hierarchy + [self._id]
        return [self._id]

    @cached_property
    def object_hierarchy(self):
        if self.parent:
            return self.parent.object_hierarchy + [self]
        return [self]

    @classmethod
    def create(cls, text, provider, parent=None, bepress_subject=None):
        validate_subject_hierarchy_length(parent)
        validate_subject_provider_mapping(provider, bepress_subject)
        subject = cls(text=text, provider=provider, parent=parent, bepress_subject=bepress_subject)
        subject.save()
        return subject

    def save(self, *args, **kwargs):
        if PreprintService.objects.filter(subjects=self).exists():
            raise ValidationError('Cannot edit a used Subject')
        return super(Subject, self).save()

    def delete(self, *args, **kwargs):
        if PreprintService.objects.filter(subjects=self).exists():
            raise ValidationError('Cannot delete a used Subject')
        return super(Subject, self).delete()
