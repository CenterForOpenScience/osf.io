from __future__ import unicode_literals

from osf.models.node import AbstractNode, AbstractNodeManager
from osf.exceptions import NodeStateError


class QuickFilesNodeManager(AbstractNodeManager):

    def create_for_user(self, user):
        possessive_title = get_quickfiles_project_title(user)

        quickfiles, created = QuickFilesNode.objects.get_or_create(
            title=possessive_title,
            creator=user
        )

        if not created:
            raise NodeStateError('Users may only have one quickfiles project')

        quickfiles.add_addon('osfstorage', auth=None, log=False)

        return quickfiles

    def get_for_user(self, user):
        return QuickFilesNode.objects.get(creator=user)


class QuickFilesNode(AbstractNode):
    __guid_min_length__ = 10

    objects = QuickFilesNodeManager()

    def __init__(self, *args, **kwargs):
        kwargs['is_public'] = True
        super(QuickFilesNode, self).__init__(*args, **kwargs)

    def remove_node(self, auth, date=None):
        # QuickFilesNodes are only delete-able for disabled users
        # This is only done when doing a GDPR-delete
        if auth.user.is_disabled:
            super(QuickFilesNode, self).remove_node(auth=auth, date=date)
        else:
            raise NodeStateError('A QuickFilesNode may not be deleted.')

    def set_privacy(self, permissions, *args, **kwargs):
        raise NodeStateError('You may not set privacy for a QuickFilesNode.')

    def add_contributor(self, contributor, *args, **kwargs):
        raise NodeStateError('A QuickFilesNode may not have additional contributors.')

    def clone(self):
        raise NodeStateError('A QuickFilesNode may not be forked, used as a template, or registered.')

    def add_addon(self, name, auth, log=True):
        if name != 'osfstorage':
            raise NodeStateError('A QuickFilesNode can only have the osfstorage addon.')
        return super(QuickFilesNode, self).add_addon(name, auth, log)

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

    @property
    def is_disabled(self):
        return self.creator.is_disabled


def get_quickfiles_project_title(user):
    possessive_title_name = user.fullname + "'s" if user.fullname[-1] != 's' else user.fullname + "'"
    return '{} Quick Files'.format(possessive_title_name)
