import mock

from modularodm import Q

from framework.auth import Auth

from tests.base import OsfTestCase
from tests.factories import ProjectFactory

from website.addons.osfstorage import model, oldels

from scripts.osfstorage import migrate_from_oldels as migration


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

    def test_migrates_files(self):
        names = []
        for num in range(10):
            names.append('DEAR GOD! {} CARPNADOS'.format(num))
            oldels.OsfStorageFileRecord.get_or_create(names[-1], self.node_settings)

        assert len(self.node_settings.file_tree.children) == 10

        migration.migrate_node_settings(self.node_settings, dry=False)
        migration.migrate_children(self.node_settings, dry=False)

        children = self.node_settings.root_node.children

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
            paths.remove(guid.path)
        assert len(paths) == 0

    def test_migrate_logs(self):
        names = []
        for num in range(10):
            names.append('DEAR GOD! {} CARPNADOS'.format(num))
            x, _ = oldels.OsfStorageFileRecord.get_or_create(names[-1], self.node_settings)
            x.delete(None)
            self.project.logs[-1].params['path'] = x.path
            self.project.logs[-1].save()

            if num % 2 == 0:
                x.undelete(None)
                self.project.logs[-1].params['path'] = x.path
                self.project.logs[-1].save()

        migration.migrate_node_settings(self.node_settings, dry=False)
        migration.migrate_children(self.node_settings, dry=False)

        for log in self.project.logs:
            if log.action.startswith('osf_storage_file'):
                path = log.params['path']
                node = self.node_settings.root_node.find_child_by_name(path.strip('/'))
                print(log)
                assert node._id in log.params['urls']['view']
                assert node._id in log.params['urls']['download']


