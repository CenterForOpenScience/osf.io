# -*- coding: utf-8 -*-
import re

from django.db import models

from framework.exceptions import PermissionsError
from website.util.permissions import ADMIN

from osf_models.models.node import AbstractNode
from osf_models.models.subject import Subject
from osf_models.models.preprint_provider import PreprintProvider
from osf_models.exceptions import ValidationValueError

# TODO DELETE ME POST MIGRATION
from modularodm import Q as MQ
# /TODO DELETE ME POST MIGRATION

def validate_doi(value):
    # DOI must start with 10 and have a slash in it - avoided getting too complicated
    if not re.match('10\\.\\S*\\/', value):
        raise ValidationValueError('"{}" is not a valid DOI'.format(value))
    return True

class Preprint(AbstractNode):
    # TODO DELETE ME POST MIGRATION
    modm_model_path = 'website.project.model.Node'
    modm_query = MQ('preprint_file', 'ne', None) | MQ('_is_preprint_orphan', 'eq', True)
    # /TODO DELETE ME POST MIGRATION

    # TODO: Uncomment when StoredFileNode is implemented
    # file = models.ForeignKey('StoredFileNode', on_delete=models.SET_NULL, null=True, blank=True)

    preprint_created = models.DateTimeField(null=True, blank=True)
    subjects = models.ManyToManyField(Subject, related_name='preprints')
    providers = models.ManyToManyField(PreprintProvider, related_name='preprints')
    doi = models.CharField(max_length=128, null=True, blank=True, validators=[validate_doi])
    _is_orphan = models.NullBooleanField(default=False)

    @classmethod
    def migrate_from_modm(cls, modm_obj):
        django_obj = super(Preprint, cls).migrate_from_modm(modm_obj)
        django_obj.doi = modm_obj.preprint_doi
        django_obj._is_orphan = modm_obj._is_preprint_orphan
        return django_obj

    @property
    def is_preprint(self):
        """For v1 compat."""
        return True

    def add_preprint_provider(self, preprint_provider, user, save=False):
        if not self.has_permission(user, ADMIN):
            raise PermissionsError('Only admins can update a preprint provider.')
        if not preprint_provider:
            raise ValueError('Must specify a provider to set as the preprint_provider')
        self.providers.add(preprint_provider)
        if save:
            self.save()

    def remove_preprint_provider(self, preprint_provider, user, save=False):
        if not self.has_permission(user, ADMIN):
            raise PermissionsError('Only admins can remove a preprint provider.')
        if not preprint_provider:
            raise ValueError('Must specify a provider to remove from this preprint.')
        if self.providers.filter(id=preprint_provider.id).exists():
            self.providers.remove(preprint_provider)
            if save:
                self.save()
            return True
        return False

    def set_preprint_subjects(self, preprint_subjects, auth, save=False):
        if not self.has_permission(auth.user, ADMIN):
            raise PermissionsError('Only admins can change a preprint\'s subjects.')

        self.subjects.clear()
        self.subjects.add(
            *Subject.objects.filter(guid__object_id__in=preprint_subjects).values_list('pk', flat=True)
        )
        if save:
            self.save()

    def set_preprint_file(self, preprint_file, auth, save=False):
        if not self.has_permission(auth.user, ADMIN):
            raise PermissionsError('Only admins can change a preprint\'s primary file.')

        # TODO: Uncomment when StoredFileNode is implemented
        # if not isinstance(preprint_file, StoredFileNode):
        #     preprint_file = preprint_file.stored_object
        #
        # if preprint_file.node != self or preprint_file.provider != 'osfstorage':
        #     raise ValueError('This file is not a valid primary file for this preprint.')
        #
        # # there is no preprint file yet! This is the first time!
        # if not self.preprint_file:
        #     self.preprint_file = preprint_file
        #     self.preprint_created = datetime.datetime.utcnow()
        #     self.add_log(action=NodeLog.PREPRINT_INITIATED, params={}, auth=auth, save=False)
        # elif preprint_file != self.preprint_file:
        #     # if there was one, check if it's a new file
        #     self.preprint_file = preprint_file
        #     self.add_log(
        #         action=NodeLog.PREPRINT_FILE_UPDATED,
        #         params={},
        #         auth=auth,
        #         save=False,
        #     )
        # if not self.is_public:
        #     self.set_privacy(
        #         Node.PUBLIC,
        #         auth=None,
        #         log=True
        #     )
        # if save:
        #     self.save()
