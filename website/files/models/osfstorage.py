from __future__ import unicode_literals

import os

from modularodm import Q

from website.files import exceptions
from website.files.models.base import File, Folder, FileNode, FileVersion


__all__ = ('OsfStorageFile', 'OsfStorageFolder', 'OsfStorageFileNode')


class OsfStorageFileNode(FileNode):
    provider = 'osfstorage'

    @classmethod
    def get(cls, _id, node):
        return cls.find_one(Q('_id', 'eq', _id) & Q('node', 'eq', node))

    @property
    def kind(self):
        return 'file' if self.is_file else 'folder'

    @property
    def materialized_path(self):
        """creates the full path to a the given filenode
        Note: Possibly high complexity/ many database calls
        USE SPARINGLY
        """
        if not self.parent:
            return '/'
        # Note: ODM cache can be abused here
        # for highly nested folders calling
        # list(self.__class__.find(Q(nodesetting),Q(folder))
        # may result in a massive increase in performance
        def lineage():
            current = self
            while current:
                yield current
                current = current.parent

        path = os.path.join(*reversed([x.name for x in lineage()]))
        if self.is_file:
            return '/{}'.format(path)
        return '/{}/'.format(path)

    def save(self):
        path = '/' + self._id + ('' if self.is_file else '/')
        if not self.path or self.path != path:
            self.path = path
        self.materialized_path = ''
        super(OsfStorageFileNode, self).save()


class OsfStorageFile(OsfStorageFileNode, File):

    def touch(self, version=-1, revision=None, **kwargs):
        try:
            return self.get_version(int(revision or version))
        except ValueError:
            return None

    @property
    def history(self):
        return [v.metadata for v in self.versions]

    def serialize(self, include_full=None):
        ret = super(OsfStorageFile, self).serialize()
        if include_full:
            ret['fullPath'] = self.materialized_path
        return ret

    def create_version(self, creator, location, metadata=None):
        latest_version = self.get_version()
        version = FileVersion(identifier=len(self.versions) + 1, creator=creator, location=location)

        if latest_version and latest_version.is_duplicate(version):
            return latest_version

        if metadata:
            version.update_metadata(metadata)

        version._find_matching_archive(save=False)

        version.save()
        self.versions.append(version)
        self.save()

        return version

    def get_version(self, version=-1, required=False):
        try:
            return self.versions[version]
        except IndexError:
            if required:
                raise exceptions.VersionNotFoundError(version)
            return None


class OsfStorageFolder(OsfStorageFileNode, Folder):

    def serialize(self, include_full=None):
        ret = super(OsfStorageFolder, self).serialize()
        if include_full:
            ret['fullPath'] = self.materialized_path
        return ret
