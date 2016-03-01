"""website.files.models.ext is home to subclasses of FileNode that provide
additional functionality and have no place in website.files.models.base
"""
import os

from website.files.models.base import FileNode


class PathFollowingFileNode(FileNode):
    """A helper class that will attempt to track the its file
    through changes in the parent addons settings
    ie: Moving you dropbox director up or down X levels
    stored_object's path will always be the full path
    from the providers root directory
    """

    FOLDER_ATTR_NAME = 'folder'

    @classmethod
    def get_or_create(cls, node, path):
        """Forces path to extend to the add-on's root directory
        """
        node_settings = node.get_addon(cls.provider)
        path = os.path.join(getattr(node_settings, cls.FOLDER_ATTR_NAME).strip('/'), path.lstrip('/'))
        return super(PathFollowingFileNode, cls).get_or_create(node, '/' + path)

    @property
    def path(self):
        """Mutates the underlying stored_object's path to be relative to _get_connected_path
        """
        return '/' + self.stored_object.path.replace(self._get_connected_path(), '', 1).lstrip('/')

    def _get_connected_path(self):
        """Returns the path of the connected provider add-on
        >>> pffn._get_connected_path()  # /MyDropbox/FolderImSharingOnTheOsf
        """
        node_settings = self.node.get_addon(self.provider)
        assert node_settings is not None, 'Connected node has no {} account'.format(self.provider)
        return getattr(node_settings, self.FOLDER_ATTR_NAME).strip('/')
