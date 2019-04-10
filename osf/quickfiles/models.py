# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.core.exceptions import ValidationError


from django.contrib.contenttypes.models import ContentType
from osf.models import BaseFileNode, Folder, TrashedFileNode, OSFUser
from osf.models.mixins import CleanMixin


class QuickFolder(BaseFileNode, Folder, CleanMixin):
    """
    QuickFolder's a are specialized OsfStorageFolder models that are attached to the user instead of a
    project, preprint, registration etc. QuickFolders have a few special restrictions normal Folder models don't have.

    1. They must have a flat file structure. Quickfolders can have no parents nor can it's children be folders.
    2. They must be attached to a user on creation, meaning the their target must always be a OSFUser instance.
    3. If a user is deleted, disabled or marked as spam that user's quickfiles must become inaccessible.
    4. Quickfiles must appear in ES results unless the user is deleted, disabled or marked as spam.
    5. When loggable events (file uploads, renames .etc) happen to Quickfiles they are logged with that user's info,
    though currently user logs aren't displayed.
    6. A Quickfolder's title must reflect user's name in a grammatically correct way.
    7. When a Quickfile is viewed/downloaded it only counts toward the metrics if the view/download is done by a user
    who doesn't own the Quickfolder that file was in.
    """
    _provider = 'osfstorage'
    DIRTY_TARGET_MSG = 'QuickFolder target must be an OSFUser'
    DIRTY_PARENT_MSG = 'parent must be none'
    DIRTY_PATH_MSG = 'path must be \'/\'/'
    DIRTY_CONTENT_TYPE_MSG = 'ContentType must be OSFUser'

    @CleanMixin.cleans_field('parent')
    def _clean_parent(self, value):
        if value is not None:
            raise ValidationError(self.DIRTY_PARENT_MSG)

    @CleanMixin.cleans_field('target')
    def _clean_target(self, value):
        if not isinstance(value, OSFUser):
            raise ValidationError(self.DIRTY_TARGET_MSG)

    @CleanMixin.cleans_field('target_content_type')
    def _clean_target_content_type(self, value):
        if not ContentType.objects.get_for_model(OSFUser) == value:
            raise ValidationError(self.DIRTY_CONTENT_TYPE_MSG)

    @property
    def title(self):
        fullname = self.target.fullname
        possessive_title_name = fullname + "'s" if fullname[-1] != 's' else fullname + "'"
        return '{} Quick Files'.format(possessive_title_name)

    @property
    def logs(self):
        return self.target.logs

    @property
    def path(self):
        return '/'

    def append_folder(self, name):
        raise NotImplementedError('Folder creation is illegal for Quickfiles')

    # Only used in v1 and tests
    def find_child_by_name(self, name, **kwargs):
        return self._children.exclude(type__in=TrashedFileNode._typedmodels_subtypes).get(name=name)
