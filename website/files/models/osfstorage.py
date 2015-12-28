from __future__ import unicode_literals

import os

from modularodm import Q

from framework.auth import Auth
from website.files import exceptions
from website.files.models.base import File, Folder, FileNode, FileVersion
from website.project.model import NodeLog
from website.project.signals import file_checkout_toggle


__all__ = ('OsfStorageFile', 'OsfStorageFolder', 'OsfStorageFileNode')


class OsfStorageFileNode(FileNode):
    provider = 'osfstorage'

    @classmethod
    def get(cls, _id, node):
        return cls.find_one(Q('_id', 'eq', _id) & Q('node', 'eq', node))

    @classmethod
    def get_or_create(cls, node, path):
        """Override get or create for osfstorage
        Path is always the _id of the osfstorage filenode.
        Use load here as its way faster than find.
        Just manually assert that node is equal to node.
        """
        inst = cls.load(path.strip('/'))
        # Use _id as odms default comparison mucks up sometimes
        if inst and inst.node._id == node._id:
            return inst

        # Dont raise anything a 404 will be raised later
        return cls.create(node=node, path=path)

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

    @property
    def path(self):
        """Path is dynamically computed as storedobject.path is stored
        as an empty string to make the unique index work properly for osfstorage
        """
        return '/' + self._id + ('' if self.is_file else '/')

    @property
    def is_checked_out(self):
        return self.checkout is not None

    def delete(self, user=None, parent=None):
        if self.is_checked_out:
            raise exceptions.FileNodeCheckedOutError()
        return super(OsfStorageFileNode, self).delete(user=user, parent=parent)

    def move_under(self, destination_parent, name=None):
        if self.is_checked_out:
            raise exceptions.FileNodeCheckedOutError()
        return super(OsfStorageFileNode, self).move_under(destination_parent, name)

    def save(self):  # TODO write log
        """
        Uses OsfSFN save to save the node,
            but we want to log specific activities (checkout, checkin)
            check that via the if in the middle of the method and log the correct activity

        :return:
        """
        self.path = ''
        self.materialized_path = ''
        ret = super(OsfStorageFileNode, self).save()

        if 'checkout' in ret and len(ret) == 1:
            # Set parameters
            auth = Auth(user=self.node.creator)

            # is checkout vs is checkin
            action = [lambda: NodeLog.CHECKED_IN, lambda: NodeLog.CHECKED_OUT][self.is_checked_out]()

            # Log the action
            self.node.add_log(
                action,
                params={
                    'project': self.node.parent_id,
                    'node': self.node._id
                },
                auth=auth,
            )

            file_checkout_toggle.send(self.node, user=self.node.creator)

        return ret


class OsfStorageFile(OsfStorageFileNode, File):

    def touch(self, bearer, version=None, revision=None, **kwargs):
        try:
            return self.get_version(revision or version)
        except ValueError:
            return None

    @property
    def history(self):
        return [v.metadata for v in self.versions]

    def serialize(self, include_full=None, version=None):
        ret = super(OsfStorageFile, self).serialize()
        if include_full:
            ret['fullPath'] = self.materialized_path

        version = self.get_version(version)
        return dict(
            ret,
            version=len(self.versions),
            md5=version.metadata.get('md5') if version else None,
            sha256=version.metadata.get('sha256') if version else None,
        )

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

    def get_version(self, version=None, required=False):
        if version is None:
            if self.versions:
                return self.versions[-1]
            return None

        try:
            return self.versions[int(version) - 1]
        except (IndexError, ValueError):
            if required:
                raise exceptions.VersionNotFoundError(version)
            return None

    def delete(self, user=None, parent=None):
        from website.search import search
        search.update_file(self, delete=True)
        return super(OsfStorageFile, self).delete(user, parent)

    def save(self, skip_search=False):
        from website.search import search
        ret = super(OsfStorageFile, self).save()
        if not skip_search:
            search.update_file(self)
        return ret

class OsfStorageFolder(OsfStorageFileNode, Folder):

    @property
    def is_checked_out(self):
        if self.checkout:
            return True
        for child in self.children:
            if child.is_checked_out:
                return True
        return False

    def serialize(self, include_full=False, version=None):
        # Versions just for compatability
        ret = super(OsfStorageFolder, self).serialize()
        if include_full:
            ret['fullPath'] = self.materialized_path
        return ret
