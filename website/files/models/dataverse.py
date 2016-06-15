from framework.auth.core import _get_current_user

from website.files.models.base import File, Folder, FileNode, FileVersion
import pdb

__all__ = ('DataverseFile', 'DataverseFolder', 'DataverseFileNode')


class DataverseFileNode(FileNode):
    provider = 'dataverse'


class DataverseFolder(DataverseFileNode, Folder):
    pass


class DataverseFile(DataverseFileNode, File):
    version_identifier = 'version'

    def update(self, revision, data, user=None):
        """Note: Dataverse only has psuedo versions, don't save them
        Dataverse requires a user for the weird check below
        and Django dies when _get_current_user is called
        """
        self.name = data['name']
        self.materialized_path = data['materialized']
        self.save()

        version = FileVersion(identifier=revision)
        version.update_metadata(data, save=False)

        user = user or _get_current_user()
        if not user or not self.node.can_edit(user=user):
            try:
                # Users without edit permission can only see published files
                if not data['extra']['hasPublishedVersion']:
                    # Blank out name and path for the render
                    # Dont save because there's no reason to persist the change
                    self.name = ''
                    self.materialized_path = ''
                    return (version, '<div class="alert alert-info" role="alert">This file does not exist.</div>')
            except (KeyError, IndexError):
                pass
        return version
