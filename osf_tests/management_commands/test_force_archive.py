import pytest
from django.utils import timezone

from addons.osfstorage.models import OsfStorageFile, OsfStorageFolder
from osf.models import NodeLog, BaseFileNode
from osf.models.files import TrashedFileNode, TrashedFolder
from osf.management.commands.force_archive import get_file_obj_from_log, build_file_tree, handle_file_operation, DEFAULT_PERMISSIBLE_ADDONS
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

    @pytest.mark.django_db
    def test_obj_cache_includes_folders(self, node, reg, permissible_addons):
        """
        Regression: n.files is a GenericRelation to OsfStorageFile only, so folder _ids were
        never in obj_cache. The fix uses BaseFileNode.objects.filter(...) which includes folders.
        """
        from django.contrib.contenttypes.models import ContentType

        folder = OsfStorageFolder.create(target=node, name='myfolder')
        folder.save()
        root_folder = OsfStorageFolder.create(target=node, name='')
        root_folder.save()

        # Demonstrate the BUG: n.files (GenericRelation to OsfStorageFile) omits folders
        old_obj_cache = set(node.files.values_list('_id', flat=True))
        assert folder._id not in old_obj_cache, 'Folders must NOT appear via n.files (demonstrating the bug)'
        assert root_folder._id not in old_obj_cache, 'Root folder must NOT appear via n.files (demonstrating the bug)'

        # Demonstrate the FIX: BaseFileNode.objects.filter(...) includes files AND folders
        ct_id = ContentType.objects.get_for_model(node.__class__()).id
        new_obj_cache = set(
            BaseFileNode.objects.filter(
                target_object_id=node.id,
                target_content_type_id=ct_id,
            ).values_list('_id', flat=True)
        )
        assert folder._id in new_obj_cache, 'Folders must appear in fixed obj_cache'
        assert root_folder._id in new_obj_cache, 'Root folder must appear in fixed obj_cache'


class TestHandleFileOperation:

    @pytest.fixture
    def node(self):
        return NodeFactory(title='Test Node', category='project')

    @pytest.fixture
    def reg(self, node):
        return RegistrationFactory(project=node, registered_date=timezone.now())

    @pytest.mark.django_db
    def test_addon_file_moved_from_root_dir(self, node, reg):
        """
        Regression: when materialized='/' (root dir moved between nodes), the old code did:
            '/{}'.format('/').rstrip('/') -> ''
            ''.split('/') -> ['']          (only 1 element)
            [''][-2]                       -> IndexError: list index out of range
        The fix detects the root-dir case and looks up the folder by name='' directly.
        """
        from django.contrib.contenttypes.models import ContentType

        root_folder = OsfStorageFolder.create(target=node, name='')
        root_folder.save()
        file = OsfStorageFile.create(target=node, name='file.txt')
        file.save()
        file.move_under(root_folder)

        ct_id = ContentType.objects.get_for_model(node.__class__()).id
        obj_cache = set(
            BaseFileNode.objects.filter(
                target_object_id=node.id,
                target_content_type_id=ct_id,
            ).values_list('_id', flat=True)
        )

        file_tree = {
            'object': root_folder,
            'name': '',
            'deleted': False,
            'version': None,
            'children': [
                {'object': file, 'name': 'file.txt', 'deleted': False, 'version': None, 'children': []}
            ]
        }

        # materialized='/' is the actual crash case: moving a root dir between nodes
        log = NodeLog.objects.create(
            node=node,
            action='addon_file_moved',
            params={
                'source': {
                    'materialized': '/',  # root dir: triggers IndexError in old code
                    'name': '',
                },
                'destination': {
                    'materialized': '/',
                    'name': '',
                }
            },
            date=timezone.now(),
        )

        # Old code: '/{}'.format('/').rstrip('/') = '' -> ''.split('/')[-2] -> IndexError
        # Fixed code: detects no '/' in materialized.rstrip('/') and uses name='' directly
        result_tree, noop = handle_file_operation(file_tree, reg, file, log, obj_cache)
        assert result_tree is not None
