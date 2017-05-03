# -*- coding: utf-8 -*-
from django.db import models
from django.db.models import Q
from django.core.exceptions import ValidationError
from django.utils.functional import cached_property
from include import IncludeQuerySet

from website.util import api_v2_url

from osf.models.base import BaseModel, MODMCompatibilityQuerySet, ObjectIDMixin
from osf.models.preprint_provider import PreprintProvider
from osf.models.validators import validate_subject_hierarchy_length, validate_subject_provider_mapping

class SubjectQuerySet(MODMCompatibilityQuerySet, IncludeQuerySet):
    def include_children(self):
        return (self | Subject.objects.filter(Q(parent__in=self) | Q(parent__parent__in=self)))

class Subject(ObjectIDMixin, BaseModel):
    """A subject discipline that may be attached to a preprint."""

    text = models.CharField(null=False, max_length=256)  # max length on prod: 73
    parent = models.ForeignKey('self', related_name='children', null=True, blank=True, on_delete=models.SET_NULL, validators=[validate_subject_hierarchy_length])
    bepress_subject = models.ForeignKey('self', related_name='aliases', null=True, blank=True, on_delete=models.deletion.CASCADE)
    provider = models.ForeignKey(PreprintProvider, related_name='subjects', on_delete=models.deletion.CASCADE)

    objects = SubjectQuerySet.as_manager()

    class Meta:
        base_manager_name = 'objects'
        unique_together = ('text', 'provider')

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
    def bepress_text(self):
        if self.bepress_subject:
            return self.bepress_subject.text
        return self.text

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

    def save(self, *args, **kwargs):
        validate_subject_provider_mapping(self.provider, self.bepress_subject)
        if self.pk and self.preprint_services.exists():
            raise ValidationError('Cannot edit a used Subject')
        return super(Subject, self).save()

    def delete(self, *args, **kwargs):
        if self.preprint_services.exists():
            raise ValidationError('Cannot delete a used Subject')
        return super(Subject, self).delete()
