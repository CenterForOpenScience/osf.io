from website.files.models.base import File, Folder, FileNode
# from website.files.models.ext import PathFollowingFileNode


__all__ = ('GoogleDriveFile', 'GoogleDriveFolder', 'GoogleDriveFileNode')


# TODO make googledrive "pathfollowing"
# A migration will need to be run that concats
# folder_path and filenode.path
# class GoogleDriveFileNode(PathFollowingFileNode):
class GoogleDriveFileNode(FileNode):
    provider = 'googledrive'
    FOLDER_ATTR_NAME = 'folder_path'


class GoogleDriveFolder(GoogleDriveFileNode, Folder):
    pass


class GoogleDriveFile(GoogleDriveFileNode, File):
    pass
