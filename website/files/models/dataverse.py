import requests

from framework.auth.core import _get_current_user

from website.files.models.base import File, Folder, FileNode, FileVersion


__all__ = ('DataverseFile', 'DataverseFolder', 'DataverseFileNode')


class DataverseFileNode(FileNode):
    provider = 'dataverse'


class DataverseFolder(DataverseFileNode, Folder):
    pass


class DataverseFile(DataverseFileNode, File):

    def touch(self, version=None, **kwargs):
        """Note: Dataverse only has psuedo versions, don't save them"""

        resp = requests.get(self.generate_metadata_url(version=version, **kwargs))
        if resp.status_code != 200:
            return None

        data = resp.json()
        self.name = data['data']['name']
        self.materialized_path = data['data']['materialized']

        version = FileVersion(identifier=version)
        version.update_metadata(data['data'], save=False)

        user = _get_current_user()
        if not user or not self.node.can_edit(user=user):
            try:
                # Users without edit permission can only see published files
                if not data['data']['extra']['hasPublishedVersion']:
                    # Blank out name and path for the render
                    # Dont save because there's no reason to persist the change
                    self.name = ''
                    self.materialized_path = ''
                    return (version, '<div class="alert alert-info" role="alert">This file does not exist.</div>')
            except (KeyError, IndexError):
                pass
