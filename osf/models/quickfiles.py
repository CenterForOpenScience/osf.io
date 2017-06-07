from __future__ import unicode_literals

import logging

from osf.models.node import AbstractNode, AbstractNodeManager
from website.exceptions import NodeStateError


logger = logging.getLogger(__name__)


class QuickFilesManager(AbstractNodeManager):

    def create_for_user(self, user):
        possessive_title = get_quickfiles_project_title(user)

        quickfiles, created = QuickFiles.objects.get_or_create(
            title=possessive_title,
            creator=user
        )

        if not created:
            raise NodeStateError('Users may only have one quickfiles project')

        quickfiles.add_addon('osfstorage', auth=None, log=False)

        return quickfiles

    def get_for_user(self, user):
        return QuickFiles.objects.get(creator=user)


class QuickFiles(AbstractNode):
    __guid_min_length__ = 10

    objects = QuickFilesManager()

    def __init__(self, *args, **kwargs):
        kwargs['is_public'] = True
        super(QuickFiles, self).__init__(*args, **kwargs)

    def remove_node(self, auth, date=None):
        raise NodeStateError('A QuickFiles node may not be deleted.')

    def set_privacy(self, permissions, *args, **kwargs):
        raise NodeStateError('You may not set privacy for QuickFiles.')

    def register_node(self, *args, **kwargs):
        raise NodeStateError('A QuickFiles node may not be registered.')

    def fork_node(self, *args, **kwargs):
        raise NodeStateError('A QuickFiles node may not be forked.')

    def add_contributor(self, contributor, *args, **kwargs):
        raise NodeStateError('A QuickFiles node may not have additional contributors.')

    @property
    def is_registration(self):
        """For v1 compat."""
        return False

    @property
    def is_collection(self):
        """For v1 compat."""
        return False

    @property
    def is_quickfiles(self):
        return True


def get_quickfiles_project_title(user):
    possessive_title_name = user.fullname + "'s" if user.fullname[-1] != 's' else user.fullname + "'"
    return '{} Quick Files'.format(possessive_title_name)
