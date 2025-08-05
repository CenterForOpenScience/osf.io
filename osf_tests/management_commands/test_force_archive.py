import pytest
from django.utils import timezone

from addons.osfstorage.models import OsfStorageFile, OsfStorageFolder
from osf.models import NodeLog, BaseFileNode
from osf.models.files import TrashedFileNode, TrashedFolder
from osf.management.commands.force_archive import get_file_obj_from_log, build_file_tree, DEFAULT_PERMISSIBLE_ADDONS
from osf_tests.factories import NodeFactory, RegistrationFactory


class TestGetFileObjFromLog:

    @pytest.fixture
    def node(self):
        return NodeFactory(title='Test Node', category='project')

    @pytest.fixture
    def reg(self, node):
        return RegistrationFactory(project=node, registered_date=timezone.now())

    @pytest.mark.django_db
    def test_file_added(self, node, reg):
        file = OsfStorageFile.objects.create(target=node, name='file1.txt')
        file.save()
        log = NodeLog.objects.create(
            node=node,
            action='osf_storage_file_added',
            params={'urls': {'view': f'/{node._id}/files/osfstorage/{file._id}/'}},
            date=timezone.now(),
        )
        file_obj = get_file_obj_from_log(log, reg)
        assert isinstance(file_obj, BaseFileNode)
        assert file_obj == file

    @pytest.mark.django_db
    def test_file_removed(self, node, reg):
        file = OsfStorageFile.create(target=node, name='trashed.txt')
        file.delete()
        log = NodeLog.objects.create(
            node=node,
            action='osf_storage_file_removed',
            params={'path': '/folder1/trashed.txt'},
            date=timezone.now(),
        )
        file_obj = get_file_obj_from_log(log, reg)
        assert isinstance(file_obj, TrashedFileNode)
        assert file_obj == file

        folder = OsfStorageFolder.create(target=node, name='folder1')
        folder.delete()
        log = NodeLog.objects.create(
            node=node,
            action='osf_storage_file_removed',
            params={'path': '/folder1/'},
            date=timezone.now(),
        )
        file_obj = get_file_obj_from_log(log, reg)
        assert isinstance(file_obj, TrashedFolder)
        assert file_obj == folder

    @pytest.mark.django_db
    def test_folder_created(self, node, reg):
        folder = OsfStorageFolder.create(target=node, name='folder1')
        folder.save()
        log = NodeLog.objects.create(
            node=node,
            action='osf_storage_folder_created',
            params={'path': '/folder1/'},
            date=timezone.now(),
        )
        file_obj = get_file_obj_from_log(log, reg)
        assert isinstance(file_obj, OsfStorageFolder)
        assert file_obj == folder

    @pytest.mark.django_db
    def test_move_rename(self, node, reg):
        file = OsfStorageFile.create(target=node, name='file2.txt')
        file.save()
        log = NodeLog.objects.create(
            node=node,
            action='addon_file_renamed',
            params={
                'source': {'path': f'/{file._id}', 'name': 'file1.txt'},
                'destination': {'path': f'/{file._id}', 'name': 'file2.txt'}
            },
            date=timezone.now(),
        )
        file_obj = get_file_obj_from_log(log, reg)
        assert isinstance(file_obj, BaseFileNode)
        assert file_obj == file

    @pytest.mark.django_db
    def test_generic_fallback(self, node, reg):
        file = OsfStorageFile.create(target=node, name='fallback.txt')
        file.save()
        log = NodeLog.objects.create(
            node=node,
            action='some_other_action',
            params={'path': '/fallback.txt'},
            date=timezone.now(),
        )
        file_obj = get_file_obj_from_log(log, reg)
        assert file_obj == file

    @pytest.mark.django_db
    def test_file_multiple_creations_deletions(self, node, reg):
        file1 = OsfStorageFile.create(target=node, name='duplicate.txt')
        file1.save()
        file1.delete()
        log1 = NodeLog.objects.create(
            node=node,
            action='osf_storage_file_removed',
            params={'path': '/duplicate.txt'},
            date=timezone.now(),
        )

        file2 = OsfStorageFile.create(target=node, name='duplicate.txt')
        file2.save()
        file2.delete()
        log2 = NodeLog.objects.create(
            node=node,
            action='osf_storage_file_removed',
            params={'path': '/duplicate.txt'},
            date=timezone.now(),
        )

        file3 = OsfStorageFile.create(target=node, name='duplicate.txt')
        file3.save()
        log3 = NodeLog.objects.create(
            node=node,
            action='osf_storage_file_added',
            params={'urls': {'view': f'/{node._id}/files/osfstorage/{file3._id}/'}},
            date=timezone.now(),
        )

        file_obj1 = get_file_obj_from_log(log1, reg)
        assert file_obj1 == file1
        assert isinstance(file_obj1, TrashedFileNode)

        file_obj2 = get_file_obj_from_log(log2, reg)
        assert file_obj2 == file2
        assert isinstance(file_obj2, TrashedFileNode)

        file_obj3 = get_file_obj_from_log(log3, reg)
        assert file_obj3 == file3
        assert isinstance(file_obj3, OsfStorageFile)


class TestBuildFileTree:

    @pytest.fixture
    def node(self):
        return NodeFactory(title='Test Node', category='project')

    @pytest.fixture
    def reg(self, node):
        return RegistrationFactory(project=node, registered_date=timezone.now())

    @pytest.fixture
    def permissible_addons(self):
        return DEFAULT_PERMISSIBLE_ADDONS

    @pytest.mark.django_db
    def test_empty_folder(self, node, reg, permissible_addons):
        folder = OsfStorageFolder.create(target=node, name='empty')
        folder.save()

        class DummyNodeSettings:
            def get_root(self):
                return folder

        node_settings = DummyNodeSettings()
        tree = build_file_tree(reg, node_settings, permissible_addons=permissible_addons)
        assert tree['object'] == folder
        assert tree['children'] == []

    @pytest.mark.django_db
    def test_nested_folders(self, node, reg, permissible_addons):
        parent = OsfStorageFolder.create(target=node, name='parent')
        parent.save()

        child = OsfStorageFolder.create(target=node, name='child')
        child.save()
        child.move_under(parent)

        file = OsfStorageFile.objects.create(target=node, name='file1.txt')
        file.save()
        file.move_under(child)

        class DummyNodeSettings:
            def get_root(self):
                return parent

        node_settings = DummyNodeSettings()
        tree = build_file_tree(reg, node_settings, permissible_addons=permissible_addons)
        assert tree['object'] == parent

        child_node = next((c for c in tree['children'] if c['object'] == child), None)
        assert child_node is not None
        assert any(grandchild['object'] == file for grandchild in child_node['children'])

    @pytest.mark.django_db
    def test_active_and_trashed_children(self, node, reg, permissible_addons):
        folder = OsfStorageFolder.create(target=node, name='parent')
        folder.save()

        file = OsfStorageFile.create(target=node, name='file1.txt')
        file.save()
        file.move_under(folder)

        deleted_file = OsfStorageFile.create(target=node, name='file2.txt')
        deleted_file.save()
        deleted_file.move_under(folder)
        deleted_file.delete()

        class DummyNodeSettings:
            def get_root(self):
                return folder

        node_settings = DummyNodeSettings()
        tree = build_file_tree(reg, node_settings, permissible_addons=permissible_addons)
        assert tree['object'] == folder

        names = [child['object'].name for child in tree['children']]
        assert 'file1.txt' in names
        assert 'file2.txt' in names

        # make sure only valid thrashed file nodes are included
        new_reg = RegistrationFactory(project=node, registered_date=timezone.now())
        file.delete()

        tree = build_file_tree(new_reg, node_settings, permissible_addons=permissible_addons)
        assert tree['object'] == folder

        names = [child['object'].name for child in tree['children']]
        assert 'file1.txt' in names
        assert 'file2.txt' not in names
