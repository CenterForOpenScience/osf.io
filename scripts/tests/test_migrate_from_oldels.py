from urllib import quote

import mock
from framework.auth import Auth
from modularodm import Q
from scripts.osfstorage import finish_oldel_migration as finishm
from scripts.osfstorage import migrate_from_oldels as migration
from tests.base import OsfTestCase
from tests.factories import ProjectFactory
from addons.osfstorage import model, oldels, utils


class TestMigrateOldels(OsfTestCase):

    def setUp(self):
        super(TestMigrateOldels, self).setUp()

        with mock.patch.object(model.OsfStorageNodeSettings, 'on_add'):
            self.project = ProjectFactory()

        self.user = self.project.creator
        self.auth = Auth(user=self.user)

        self.node_settings = self.project.get_addon('osfstorage')

        tree, _ = oldels.OsfStorageFileTree.get_or_create('', self.node_settings)
        tree.save()
        self.node_settings.file_tree = tree
        self.node_settings.save()

    def test_creates_root_node(self):
        assert self.node_settings.root_node is None
        migration.migrate_node_settings(self.node_settings, dry=False)
        assert self.node_settings.root_node is not None
        assert not self.node_settings._dirty

    def test_creates_root_node_on_none_file_tree(self):
        self.node_settings.file_tree = None
        self.node_settings.save()
        assert self.node_settings.root_node is None
        assert self.node_settings.file_tree is None
        migration.migrate_node_settings(self.node_settings, dry=False)
        assert self.node_settings.root_node is not None
        assert not self.node_settings._dirty

    def test_migrates_files(self):
        names = []
        for num in range(10):
            names.append('DEAR GOD! {} CARPNADOS'.format(num))
            oldels.OsfStorageFileRecord.get_or_create(names[-1], self.node_settings)

        assert len(self.node_settings.file_tree.children) == 10

        migration.migrate_node_settings(self.node_settings, dry=False)
        migration.migrate_children(self.node_settings, dry=False)

        children = list(model.OsfStorageFileNode.find(
            Q('parent', 'eq', self.node_settings.root_node) &
            Q('node_settings', 'eq', self.node_settings)
        ))

        assert not self.node_settings._dirty
        assert self.node_settings.root_node is not None
        assert not self.node_settings.root_node._dirty

        assert len(children) == 10

        for child in children:
            names.remove(child.name)

        assert len(names) == 0

    def test_migrates_guids(self):
        names = []
        for num in range(10):
            names.append('DEAR GOD! {} CARPNADOS'.format(num))
            guid = model.OsfStorageGuidFile(node=self.project, path=names[-1])
            guid.save()
            oldels.OsfStorageFileRecord.get_or_create(names[-1], self.node_settings)

        assert len(model.OsfStorageGuidFile.find()) == 10

        migration.migrate_node_settings(self.node_settings, dry=False)
        migration.migrate_children(self.node_settings, dry=False)

        guids = model.OsfStorageGuidFile.find()
        paths = [x.path for x in model.OsfStorageFileNode.find(Q('kind', 'eq', 'file') & Q('node_settings', 'eq', self.node_settings))]
        assert len(guids) == 10
        for guid in guids:
            paths.remove(guid._path)
        assert len(paths) == 0

        finishm.migrate()

        paths = [x.path for x in model.OsfStorageFileNode.find(Q('kind', 'eq', 'file') & Q('node_settings', 'eq', self.node_settings))]
        assert len(guids) == 10
        for guid in guids:
            paths.remove(guid.path)
        assert len(paths) == 0

        finishm.unmigrate()

        old_paths = [x.path for x in self.node_settings.file_tree.children]
        paths = [x.path for x in model.OsfStorageFileNode.find(Q('kind', 'eq', 'file') & Q('node_settings', 'eq', self.node_settings))]
        assert len(guids) == 10
        for guid in guids:
            old_paths.remove(guid.path)
            paths.remove(guid._path)
        assert len(paths) == 0
        assert len(old_paths) == 0

    def test_migrate_logs(self):
        names = []
        for num in range(10):
            names.append('DEAR GOD! {} CARPNADOS'.format(num))
            x, _ = oldels.OsfStorageFileRecord.get_or_create(names[-1], self.node_settings)
            x.delete(None)
            self.project.logs.latest().params['path'] = x.path
            self.project.logs.latest().save()

            if num % 2 == 0:
                x.undelete(None)
                self.project.logs.latest().params['path'] = x.path
                self.project.logs.latest().save()

        migration.migrate_node_settings(self.node_settings, dry=False)
        migration.migrate_children(self.node_settings, dry=False)

        for log in self.project.logs:
            if log.action.startswith('osf_storage_file'):
                path = log.params['_path']
                node = self.node_settings.root_node.find_child_by_name(path.strip('/'))
                assert node._id in log.params['_urls']['view']
                assert node._id in log.params['_urls']['download']

        finishm.migrate()

        for log in self.project.logs:
            if log.action.startswith('osf_storage_file'):
                log.reload()
                path = log.params['path']
                node = self.node_settings.root_node.find_child_by_name(path.strip('/'))
                assert node._id in log.params['urls']['view']
                assert node._id in log.params['urls']['download']

        finishm.unmigrate()

        for log in self.project.logs:
            if log.action.startswith('osf_storage_file'):
                log.reload()
                path = log.params['path'].lstrip('/')
                node = oldels.OsfStorageFileRecord.find_by_path(path, self.node_settings)
                assert quote(node.path) in log.params['urls']['view']
                assert quote(node.path) in log.params['urls']['download']

    @mock.patch('framework.analytics.session')
    def test_migrate_download_counts(self, mock_session):
        names = []
        for index, num in enumerate(range(10)):
            names.append('DEAR GOD$! ({})^ CARPNADOS'.format(num))
            fobj, _ = oldels.OsfStorageFileRecord.get_or_create(names[-1], self.node_settings)
            for _id in range(index):
                fobj.create_version(self.user, {
                    'folder': '',
                    'bucket': '',
                    'service': 'buttfiles',
                    'object': '{}{}'.format(index, _id),
                })
                utils.update_analytics(self.project, fobj.path, _id + 1)
                self.project.logs.latest().params['path'] = 'notnone'
                self.project.logs.latest().save()

            assert len(fobj.versions) == index
            assert fobj.get_download_count() == index

        assert len(self.node_settings.file_tree.children) == 10

        migration.migrate_node_settings(self.node_settings, dry=False)
        migration.migrate_children(self.node_settings, dry=False)

        children = model.OsfStorageFileNode.find(Q('kind', 'eq', 'file') & Q('node_settings', 'eq', self.node_settings))

        for index, child in enumerate(children):
            assert len(child.versions) == index
            assert child.get_download_count() == index
            for _id in range(index):
                assert child.get_download_count(_id) == 1

        for index, child in enumerate(self.node_settings.file_tree.children):
            assert len(child.versions) == index
            assert child.get_download_count() == index
            for _id in range(index):
                assert child.get_download_count(_id + 1) == 1
