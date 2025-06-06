from addons.wiki.models import WikiVersion,WikiPageNodeManager, WikiPage
from framework.auth.core import Auth
from osf_tests.factories import (
    UserFactory, NodeFactory, ProjectFactory,
    AuthUserFactory, RegistrationFactory
)

from addons.osfstorage.models import OsfStorageFolder, OsfStorageFile
from addons.wiki.utils import (
    get_sharejs_uuid, generate_private_uuid, share_db, delete_share_doc,
    migrate_uuid, format_wiki_version, serialize_wiki_settings, serialize_wiki_widget,
    check_file_object_in_node, get_numbered_name_for_existing_wiki, get_import_wiki_name_list,
    get_wiki_fullpath, _get_wiki_parent, _get_all_child_file_ids, get_node_file_mapping, copy_files_with_timestamp
)
from addons.wiki.views import (
    _get_wiki_versions,_get_wiki_child_pages_latest,_get_wiki_api_urls,project_wiki_delete
)
from osf.utils.fields import NonNaiveDateTimeField
from framework.exceptions import HTTPError
from osf.models.files import BaseFileNode
from addons.wiki.models import WikiImportTask, WikiPage, WikiVersion, render_content
from framework.auth import Auth
from django.utils import timezone
from addons.wiki import views
import time
import mock
import pytest
import pytz
import datetime
import re
import unicodedata
import uuid


pytestmark = pytest.mark.django_db

SPECIAL_CHARACTERS_ALL = u'`~!@#$%^*()-=_+ []{}\|/?.df,;:''"'
SPECIAL_CHARACTERS_ALLOWED = u'`~!@#$%^*()-=_+ []{}\|?.df,;:''"'

class TestFileNode(BaseFileNode):
    _provider = 'test',

class TestFolder(TestFileNode, Folder):
    pass

class TestFile(TestFileNode, File):
    pass

@pytest.mark.enable_bookmark_creation
class TestWikiPageNodeManager(OsfTestCase):

    def setUp(self):
        self.page_name = WikiPageNodeManager.CharField(max_length=200, validators=["test", ])
        self.user = WikiPageNodeManager.ForeignKey('osf.OSFUser', null=True, blank=True, on_delete=WikiPageNodeManager.CASCADE)
        self.node = WikiPageNodeManager.ForeignKey('osf.AbstractNode', null=True, blank=True, on_delete=WikiPageNodeManager.CASCADE, related_name='wikis')
        self.parent = WikiPageNodeManager.ForeignKey('self', null=True, blank=True, on_delete=WikiPageNodeManager.CASCADE)
        self.sort_order = WikiPageNodeManager.IntegerField(blank=True, null=True)
        self.deleted = WikiPageNodeManager.NonNaiveDateTimeField(blank=True, null=True, db_index=True)
        self.content = WikiVersion.TextField(default='', blank=True)
        self.consolidate_auth = Auth(user=self.project.creator)
        self.project = ProjectFactory()

    def test_create_for_node_true(self,mocker):
        wiki_page = WikiPage.objects.create(
            node=self.node,
            page_name=self.page_name,
            user=self.page_name,
            parent=self.parent,
            is_wiki_import=True
        )

        mock_create = mocker.patch('WikiPage.create',return_value=wiki_page)
        mock_update = mocker.patch('WikiPage.update', return_value=None)
        
        self.home_child_wiki = WikiPageNodeManager.objects.create_for_node(
            self.project,
            'home child',
            'home child content',
            self.consolidate_auth,
            parent=None,
            is_wiki_import=False)

        # True?
        mock_create.assert_called_with(is_wiki_import=True)
        mock_update.assert_called_with(is_wiki_import=True)

    def test_create_for_node_false(self,mocker):
        wiki_page = WikiPage.objects.create(
            node=self.node,
            page_name=self.page_name,
            user=self.page_name,
            parent=self.parent,
            is_wiki_import=False
        )

        mock_create = mocker.patch('WikiPage.create',return_value=wiki_page)
        mock_update = mocker.patch('WikiPage.update', return_value=None)
        
        self.home_child_wiki = WikiPageNodeManager.objects.create_for_node(
            self.project,
            'home child',
            'home child content',
            self.consolidate_auth,
            parent=None,
            is_wiki_import=False)

        # False
        mock_create.assert_called_with(is_wiki_import=False)
        mock_update.assert_called_with(is_wiki_import=False)

@pytest.mark.enable_bookmark_creation
class TestWikiPageNodeManager(OsfTestCase):
    def setUp(self):
        self.node = WikiPageNodeManager.ForeignKey('osf.AbstractNode', null=True, blank=True, on_delete=WikiPageNodeManager.CASCADE, related_name='wikis')
        self.parent = WikiPageNodeManager.ForeignKey('self', null=True, blank=True, on_delete=WikiPageNodeManager.CASCADE)

    def test_get_for_child_nodes(self, mocker):
        mock_child_node = mocker.patch('WikiPage.filter',return_value=None)
        
        child_node = WikiPageNodeManager.objects.filter(parent=self.parent, deleted__isnull=True, node=self.node)
        
        # モックが1回呼ばれたか
        mock_child_node.assert_called_once()

    def test_get_for_child_nodes_none(self):
        child_node = WikiPageNodeManager.objects.get_for_child_nodes(self,self.node,None)
        
        # 戻り値がNoneか
        self.assert_is_not_none(child_node)
    
    def test_get_wiki_pages_latest(self, mocker):
        mock_annotate = mocker.patch('WikiVersion.objects.annotate', return_value=None)
                
        # モックが1回呼ばれたか
        mock_annotate.assert_called_once()

    def test_get_wiki_child_pages_latest(self, mocker):
        mock_annotate = mocker.patch('WikiVersion.objects.annotate', return_value=None)
                
        # モックが1回呼ばれたか
        mock_annotate.assert_called_once()

    def test_create(self, mocker):
        create_node = WikiPageNodeManager.objects.create(self,False,{'status': 'unmodified', 'path': '/importpagec/importpaged'})

        self.assertIsNotNone(create_node)

@pytest.mark.enable_bookmark_creation
class TestWikiPage(OsfTestCase):
    def setUp(self):
        self.objects = WikiPageNodeManager()

        self.page_name = WikiPage.CharField(max_length=200, validators=["test", ])
        self.user = WikiPage.ForeignKey('osf.OSFUser', null=True, blank=True, on_delete=WikiPage.CASCADE)
        self.node = WikiPage.ForeignKey('osf.AbstractNode', null=True, blank=True, on_delete=WikiPage.CASCADE, related_name='wikis')
        self.parent = WikiPage.ForeignKey('self', null=True, blank=True, on_delete=WikiPage.CASCADE)
        self.sort_order = WikiPage.IntegerField(blank=True, null=True)
        self.deleted = NonNaiveDateTimeField(blank=True, null=True, db_index=True)
        self.content = WikiVersion.TextField(default='', blank=True)

    def test_update_false(self, mocker):
        mock_save = mocker.patch('WikiVersion.save')

        wiki_page = WikiPage.objects.update(
            self,
            self.user,
            self.content,
            False
        )

        # False
        mock_save.assert_called_with(is_wiki_import=False)

    def test_update_true(self, mocker):
        mock_save = mocker.patch('WikiVersion.save')

        wiki_page = WikiPage.objects.update(
            self,
            self.user,
            self.content,
            True
        )

        # True
        mock_save.assert_called_with(is_wiki_import=True)

class test_utils(OsfTestCase):
    def setUp(self):
        super(test_utils, self).setUp()
        self.user = AuthUserFactory()
        self.project1 = ProjectFactory(is_public=True, creator=self.user)
        self.consolidate_auth = Auth(user=self.project1.creator)
        self.wiki_import_dir = TestFolder.objects.create(name='wiki import dir', target=self.project1)
        self.pagefolder1 = TestFolder.objects.create(name='page1', target=self.project1, parent=self.wiki_import_dir)
        self.pagefolder2 = TestFolder.objects.create(name='page2', target=self.project1, parent=self.wiki_import_dir)
        self.pagefile1 = TestFile.objects.create(name='page1.md', target=self.project1, parent=self.pagefolder1)
        self.attachment1 = TestFile.objects.create(name='attachment1.pdf', target=self.project1, parent=self.pagefolder1)
        self.pagefile2 = TestFile.objects.create(name='page2.md', target=self.project1, parent=self.pagefolder2)
        self.attachment2 = TestFile.objects.create(name='attachment2.docx', target=self.project1, parent=self.pagefolder2)
        self.pagefolder3 = TestFolder.objects.create(name='page3', target=self.project1, parent=self.pagefolder2)
        self.pagefile3 = TestFile.objects.create(name='page3.md', target=self.project1, parent=self.pagefolder3)
        self.attachment3 = TestFile.objects.create(name='attachment3.xlsx', target=self.project1, parent=self.pagefolder3)

    
    @mock.patch('addons.wiki.views.BaseFileNode.objects.filter')
    def test_get_node_file_mapping(self, mock_filter):
        mock_filter.return_value.values_list.return_value = [
            (self.pagefile1._id, 'page1.md', 'page1'),
            (self.attachment1._id, 'attachment1.pdf', 'page1'),
            (self.pagefile2._id, 'page2.md', 'page2'),
            (self.attachment2._id, 'attachment2.docx', 'page2'),
            (self.pagefile3._id, 'page3.md', 'page3'),
            (self.attachment3._id, 'attachment3.xlsx', 'page3'),
        ]
        file_mapping = get_node_file_mapping(self.project1, self.wiki_import_dir._id)
        expected_mapping = {
            'page1^page1.md': self.pagefile1._id,
            'page1^attachment1.pdf': self.attachment1._id,
            'page2^page2.md': self.pagefile2._id,
            'page2^attachment2.docx': self.attachment2._id,
            'page3^page3.md': self.pagefile3._id,
            'page3^attachment3.xlsx': self.attachment3._id,
        }

        self.assertEqual(file_mapping, expected_mapping)
    
    def test_get_import_wiki_name_list(self):
        wiki_info = [
            {
                'parent_wiki_name': None,
                'path': '/page1',
                'original_name': 'page1',
                'wiki_name': 'page1',
                'status': 'valid',
                'message': '',
                '_id': 'xxx',
                'wiki_content': 'content1'
            },
            {
                'parent_wiki_name': None,
                'path': '/page2',
                'original_name': 'page2',
                'wiki_name': 'page2',
                'status': 'valid',
                'message': '',
                '_id': 'yyy',
                'wiki_content': 'content2'
            },
            {
                'parent_wiki_name': 'page2',
                'path': '/page2/page3',
                'original_name': 'page3',
                'wiki_name': 'page3',
                'status': 'valid',
                'message': '',
                '_id': 'zzz',
                'wiki_content': 'content3'
            }
        ]
        result = get_import_wiki_name_list(wiki_info)
        expected_result = ['page1', 'page2', 'page3']
        self.assertEqual(result, expected_result)

    def test_existing_wiki(self):
        wiki = self.child_wiki
        parent_wiki_name = self.parent_wiki.page_name
        wiki_name = wiki.page_name
        expected_result = '/' + parent_wiki_name + '/' + wiki_name
        result = get_wiki_fullpath(self.project, wiki_name)
        self.assertEqual(result, expected_result)

    def test_non_existing_wiki(self):
        result = get_wiki_fullpath(self.project, 'non existing wiki name')
        self.assertEqual(result, '')

    def test_no_matching_wiki(self):
        base_name = 'test'
        result = get_numbered_name_for_existing_wiki(self.project, base_name)
        self.assertEqual(result, '')

    def test_matching_wiki_no_number(self):
        base_name = 'Existing Wiki'
        result = get_numbered_name_for_existing_wiki(self.project, base_name)
        self.assertEqual(result, 1)

    def test_matching_wiki_with_number(self):
        base_name = 'Numbered'
        result = get_numbered_name_for_existing_wiki(self.project, base_name)
        self.assertEqual(result, 2)

    def test_matching_wiki_home(self):
        result = get_numbered_name_for_existing_wiki(self.project, 'home')
        self.assertEqual(result, 1)

    def test_correct_directory_id(self):
        dir_id = self.folder1._id
        result = check_file_object_in_node(dir_id, self.project1)
        self.assertTrue(result)

    def test_invalid_directory_id(self):
        with self.assertRaises(HTTPError) as context:
            check_file_object_in_node('invalid_directory_id', self.project1)

        self.assertEqual(context.exception.data['message_short'], 'directory id does not exist')
        self.assertEqual(context.exception.data['message_long'], 'directory id does not exist')

    def test_invalid_target_object_id(self):
        dir_id = self.folder1._id
        with self.assertRaises(HTTPError) as context:
            check_file_object_in_node(dir_id, self.project2)

        self.assertEqual(context.exception.data['message_short'], 'directory id is invalid')
        self.assertEqual(context.exception.data['message_long'], 'directory id is invalid')

    def test_copy_files_with_timestamp(self):
        src = [
            {
                'name': 'TEST',
                'path': '/page1',
                'original_name': 'page1',
                'wiki_name': 'page1',
                'status': 'valid',
                'message': '',
                '_id': 'yyy',
                'wiki_content': 'content1'
            }
        ]
        target_node = [
            {
                'name': 'TargetTest',
                'path': '/targetpage',
                'original_name': 'targetpage',
                'wiki_name': 'targetpage',
                'status': 'valid',
                'message': '',
                '_id': 'yyy',
                'wiki_content': 'content2'
            }
        ]
        parent = [
            {
                
            }
        ]

        cloned = copy_files_with_timestamp(
            self.consolidate_auth,
            src,
            target_node,
            parent=None,
            name=None)
        cloned_id = cloned._id
        return cloned_id

class test_views(OsfTestCase):
    def setUp(self):
        super(test_views, self).setUp()
        self.user = AuthUserFactory()
        self.project = ProjectFactory(is_public=True, creator=self.user)
        self.consolidate_auth = Auth(user=self.project.creator)
        self.home_wiki = WikiPage.objects.create_for_node(self.project, 'home', 'Version 1', Auth(self.user))
        self.home_wiki.update(self.user, 'Version 2')
        self.funpage_wiki = WikiPage.objects.create_for_node(self.project, 'funpage', 'Version 1', Auth(self.user))

        self.root = BaseFileNode.objects.get(target_object_id=self.project.id, is_root=True)

        # root
        #  └── rootimportfolder1
        #      └── importpage1
        #          └── importpage1.md
        self.root_import_folder1 = TestFolder.objects.create(name='rootimportfolder1', target=self.project, parent=self.root)
        self.import_page_folder1 = TestFolder.objects.create(name='importpage1', target=self.project, parent=self.root_import_folder1)
        self.import_page_md_file1 = TestFile.objects.create(name='importpage1.md', target=self.project, parent=self.import_page_folder1)

        # root
        # └── rootimportfoldera
        #     ├── importpagea
        #     │   └── importpagea.md
        #     ├── importpageb
        #     │   ├── importpageb.md
        #     │   └── pdffile.pdf
        #     └── importpagec
        #         └── importpagec.md
        self.root_import_folder_a = TestFolder.objects.create(name='rootimportfoldera', target=self.project, parent=self.root)
        self.import_page_folder_a = TestFolder.objects.create(name='importpagea', target=self.project, parent=self.root_import_folder_a)
        self.import_page_md_file_a = TestFile.objects.create(name='importpagea.md', target=self.project, parent=self.import_page_folder_a)
        self.import_page_folder_b = TestFolder.objects.create(name='importpageb', target=self.project, parent=self.root_import_folder_a)
        self.import_page_md_file_b = TestFile.objects.create(name='importpageb.md', target=self.project, parent=self.import_page_folder_b)
        self.import_page_pdf_file = TestFile.objects.create(name='pdffile.pdf', target=self.project, parent=self.import_page_folder_b)
        self.import_page_folder_c = TestFolder.objects.create(name='importpagec', target=self.project, parent=self.root_import_folder_a)
        self.import_page_md_file_c = TestFile.objects.create(name='importpagec.md', target=self.project, parent=self.import_page_folder_c)

        # existing wiki page in project1
        self.wiki_page1 = WikiPage.objects.create_for_node(self.project, 'importpagea', 'wiki pagea content', self.consolidate_auth)
        self.wiki_page2 = WikiPage.objects.create_for_node(self.project, 'importpageb', 'wiki pageb content', self.consolidate_auth)

        # importpagex
        self.root_import_folder_x = TestFolder.objects.create(name='rootimportfolderx', target=self.project, parent=self.root)
        self.import_page_folder_invalid = TestFolder.objects.create(name='importpagex', target=self.project, parent=self.root_import_folder_x)

        self.project2 = ProjectFactory(is_public=True, creator=self.user)
        self.root2 = BaseFileNode.objects.get(target_object_id=self.project2.id, is_root=True)
        self.consolidate_auth2 = Auth(user=self.project2.creator)

        # existing wiki page in project2
        self.wiki_page3 = WikiPage.objects.create_for_node(self.project2, 'importpagec', 'wiki pagec content', self.consolidate_auth2)
        self.wiki_page4 = WikiPage.objects.create_for_node(self.project2, 'importpaged', 'wiki paged content', self.consolidate_auth2, self.wiki_page3)


        self.root_import_folder_validate = OsfStorageFolder(name='rootimportfolder', target=self.project, parent=self.root)
        self.root_import_folder_validate.save()
        self.import_page_folder_1 = OsfStorageFolder(name='importpage1', target=self.project, parent=self.root_import_folder_validate)
        self.import_page_folder_1.save()
        self.import_page_md_file_1 = OsfStorageFile(name='importpage1.md', target=self.project, parent=self.import_page_folder_1)
        self.import_page_md_file_1.save()
        self.import_page_doc_file = OsfStorageFile(name='docfile.docx', target=self.project, parent=self.import_page_folder_1)
        self.import_page_doc_file.save()
        self.import_page_folder_2 = OsfStorageFolder(name='importpage2', target=self.project, parent=self.import_page_folder_1)
        self.import_page_folder_2.save()
        self.import_page_md_file_2 = OsfStorageFile(name='importpage2.md', target=self.project, parent=self.import_page_folder_2)
        self.import_page_md_file_2.save()
        self.import_page_pdf_file = OsfStorageFile(name='pdffile.pdf', target=self.project, parent=self.import_page_folder_2)
        self.import_page_pdf_file.save()

        self.data = [
            {
                'parent_wiki_name': None,
                'path': '/importpage4',
                'original_name': 'importpage4',
                'wiki_name': 'importpage4',
                'status': 'valid',
                'message': '',
                '_id': 'abc'
            },
            {
                'parent_wiki_name': 'importpage4',
                'path': '/importpage4/importpage5',
                'original_name': 'importpage5',
                'wiki_name': 'importpage5',
                'status': 'valid',
                'message': '',
                '_id': 'def'
            },
            {
                'parent_wiki_name': None,
                'path': '/importpage1',
                'original_name': 'importpage1',
                'wiki_name': 'importpage1',
                'status': 'valid',
                'message': '',
                '_id': 'ghi'
            },
            {
                'parent_wiki_name': 'importpage1',
                'path': '/importpage1/importpage2',
                'original_name': 'importpage2',
                'wiki_name': 'importpage2',
                'status': 'valid',
                'message': '',
                '_id': 'jkl'
            },
            {
                'parent_wiki_name': 'importpage2',
                'path': '/importpage1/importpage2/importpage3',
                'original_name': 'importpage3',
                'wiki_name': 'importpage3',
                'status': 'valid',
                'message': '',
                '_id': 'mno'
            }
        ]
    @mock.patch('addons.wiki.views.BaseFileNode.objects.filter')
    def test_get_wiki_version_none(self, mock_filter):
        mock_filter.return_value = None

        versions = _get_wiki_versions(None, 'test', anonymous=False)
        self.assertEqual(len(versions),0)

    @mock.patch('addons.wiki.views.BaseFileNode.objects.filter')
    def test_get_wiki_version(self, mock_filter):
        mock_filter.return_value = [
            {
                'version': 'Version 1'
            }
        ]

        versions = _get_wiki_versions(None, 'test', anonymous=False)
        self.assertGreaterEqual(len(versions),1)

    @mock.patch('addons.wiki.views.WikiPage.objects.get_wiki_child_pages_latest')
    def test_get_wiki_child_pages_latest(self, get_wiki_child_pages_latest):
        
        name = 'page by id'
        page = WikiPage.objects.create_for_node(self.project, name, 'some content', Auth(self.project.creator))

        get_wiki_child_pages_latest.return_value = page

        rtnPages = _get_wiki_child_pages_latest(None, 'test', anonymous=False)
        self.assertGreaterEqual(len(rtnPages),1)

    def test_get_wiki_api_urls(self):
        urls = _get_wiki_api_urls(self.project, self.wname)
        self.assert_equal(urls['sort'], self.project.api_url_for('project_update_wiki_page_sort'))

    @mock.patch('addons.wiki.views.WikiPage.objects.get_for_node')
    @mock.patch('addons.wiki.utils.get_sharejs_uuid')
    def test_project_wiki_delete_404Err(self, mock_get_for_node, mock_get_sharejs_uuid):
        mock_get_for_node.return_value = None
        mock_get_sharejs_uuid.return_value = None

        delete_url = self.project.api_url_for('project_wiki_delete', wname='funpage')
        self.app.delete(delete_url, auth=self.user.auth)
        #res = self.app.get(delete_url, expect_errors=True)
        res = self.app.get(delete_url)
        self.assert_equal(res.status_code, 404)

    @mock.patch('addons.wiki.views.WikiPage.objects.get_for_node')
    @mock.patch('addons.wiki.utils.get_sharejs_uuid')
    def test_project_wiki_delete_404Err(self, mock_get_for_node, mock_get_sharejs_uuid):
        mock_get_for_node.return_value = None
        mock_get_sharejs_uuid.return_value = None

        delete_url = self.project.api_url_for('project_wiki_delete', wname='funpage')
        self.app.delete(delete_url, auth=self.user.auth)
        #res = self.app.get(delete_url, expect_errors=True)
        res = self.app.get(delete_url)
        self.assert_equal(res.status_code, 404)

    @mock.patch('addons.wiki.utils.get_sharejs_uuid')
    @mock.patch('addons.wiki.views.WikiPage.objects.get_for_child_nodes')
    def test_project_wiki_delete(self, mock_get_sharejs_uuid, mock_get_for_child_nodes):
        page = self.elephant_wiki

        url = self.project.api_url_for(
            'project_wiki_delete',
            wname='Elephants'
        )
        mock_get_for_child_nodes.return_value =[
            {
                'name': 'TEST',
                'path': '/page2',
                'original_name': 'page2',
                'wiki_name': 'page2',
                'status': 'valid',
                'message': '',
                '_id': 'yyy',
                'wiki_content': 'content2'
            }
        ]
        mock_now = datetime.datetime(2017, 3, 16, 11, 00, tzinfo=pytz.utc)
        with mock.patch.object(timezone, 'now', return_value=mock_now):
            self.app.delete(
                url,
                auth=self.auth
            )
        self.project.reload()
        page.reload()
        self.asserEqual(page.deleted, mock_now)

    def test_get_import_folder_include_invalid_folder(self):
        root = BaseFileNode.objects.get(target_object_id=self.project.id, is_root=True)
        root_import_folder = OsfStorageFolder(name='rootimportfolder', target=self.project, parent=root)
        root_import_folder.save()
        import_page_folder = OsfStorageFolder(name='importpage', target=self.project, parent=root_import_folder)
        import_page_folder.save()
        import_page_md_file = OsfStorageFile(name='importpage.md', target=self.project, parent=import_page_folder)
        import_page_md_file.save()
        import_page_folder_invalid = OsfStorageFile(name='importpageinvalid.md', target=self.project, parent=root_import_folder)
        import_page_folder_invalid.save()
        result = views._get_import_folder(self.project)
        self.assertEqual(result[0] , {'id': root_import_folder._id, 'name': 'rootimportfolder'})

    def test_project_wiki_edit_post(self):
        url = self.project.web_url_for('project_wiki_edit_post', wname='home')
        res = self.app.post_json(url, {'markdown': 'new content'}, auth=self.user.auth).follow()
        self.asserEqual(res.status_code, 200)


    @mock.patch('addons.wiki.views.WikiPage.objects.get_for_node')
    @mock.patch('addons.wiki.views.WikiPage.objects.create_for_node')
    def test_wiki_validate_name(self, mock_get_for_node, mock_create_for_node):
        mock_get_for_node.return_value = [
            {
                'name': 'TEST',
                'path': '/page2',
                'original_name': 'page2',
                'wiki_name': 'page2',
                'status': 'valid',
                'message': '',
                '_id': 'yyy',
                'wiki_content': 'content2'
            }
        ]
        mock_create_for_node.return_value = None

        url = self.project.api_url_for('project_wiki_validate_name', wname='Capslock', p_wname='home', node=None)
        res = self.app.get(url, auth=self.user.auth)

        # モックが1回呼ばれたか
        mock_create_for_node.assert_called_once()

    @mock.patch('addons.wiki.views.WikiPage.objects.get_for_node')
    @mock.patch('addons.wiki.views.WikiPage.objects.create_for_node')
    def test_wiki_validate_name_404err(self, mock_get_for_node, mock_create_for_node):
        mock_get_for_node.return_value = [
            {
                'name': 'TEST',
                'path': '/page2',
                'original_name': 'page2',
                'wiki_name': 'page2',
                'status': 'valid',
                'message': '',
                '_id': 'yyy',
                'wiki_content': 'content2'
            }
        ]
        mock_create_for_node.return_value = None

        url = self.project.api_url_for('project_wiki_validate_name', wname='Capslock', p_wname='test', node=None)
        res = self.app.get(url, auth=self.user.auth)

        self.asserEqual(res.status_code, 404)

    def test_format_home_wiki_page_no_content(self):
        data = views.format_home_wiki_page(self.project)
        expected = {
            'page': {
                'url': self.project.web_url_for('project_wiki_home'),
                'name': 'Home',
                'id': 'None',
            }
        }
        self.assert_equal(data, expected)

    @mock.patch('addons.wiki.views._format_child_wiki_page')
    def test_format_project_wiki_pages(self,mock_format_child_wiki_pages):
        mock_format_child_wiki_pages.return_value = [
            {
                'name': 'Children',
                'path': '/Children',
                'original_name': 'Children',
                'wiki_name': 'Children',
                'status': 'valid',
                'message': '',
                '_id': 'yyy',
                'wiki_content': 'ChildrenContent'
            }
        ]
        self.parent_wiki_page = WikiPage.objects.create_for_node(self.project, 'parent page', 'parent content', self.consolidate_auth)
        self.child_wiki_page = WikiPage.objects.create_for_node(self.project, 'child page', 'child content', self.consolidate_auth, self.parent_wiki_page)
        self.grandchild_wiki_page = WikiPage.objects.create_for_node(self.project, 'grandchild page', 'grandchild content', self.consolidate_auth, self.child_wiki_page)
        project_format = views.format_project_wiki_pages(node=self.project, auth=self.consolidate_auth)

        self.asserEqual(project_format['kind'], 'folder')

    @mock.patch('addons.wiki.views._get_wiki_child_pages_latest')
    def test_format_child_wiki_pages(self,mock_get_wiki_child_pages_latest):
        mock_get_wiki_child_pages_latest.return_value = None

        self.parent_wiki_page = WikiPage.objects.create_for_node(self.project, 'parent page', 'parent content', self.consolidate_auth)
        self.child_wiki_page = WikiPage.objects.create_for_node(self.project, 'child page', 'child content', self.consolidate_auth, self.parent_wiki_page)
        self.grandchild_wiki_page = WikiPage.objects.create_for_node(self.project, 'grandchild page', 'grandchild content', self.consolidate_auth, self.child_wiki_page)
        project_format = views.format_project_wiki_pages(node=self.project, auth=self.consolidate_auth)

        self.assertNotEqual(project_format['kind'], 'folder')

    def test_serialize_component_wiki(self):
        home_page = WikiPage.objects.create_for_node(self.component, 'home', 'content here', self.consolidate_auth)
        zoo_page = WikiPage.objects.create_for_node(self.component, 'zoo', 'koala', self.consolidate_auth)
        expected = [
            {
                'page': {
                    'name': self.component.title,
                    'url': self.component.web_url_for('project_wiki_view', wname='home', _guid=True),
                },
                'children': [
                    {
                        'page': {
                            'url': self.component.web_url_for('project_wiki_view', wname='home', _guid=True),
                            'name': 'Home',
                            'id': self.component._primary_key,
                        },
                    },
                    {
                        'page': {
                            'url': self.component.web_url_for('project_wiki_view', wname='zoo', _guid=True),
                            'name': 'zoo',
                            'sort_order': None,
                            'id': zoo_page._primary_key,
                        },
                        'children': [],
                    }
                ],
                'kind': 'component',
                'category': self.component.category,
                'pointer': False,
            }
        ]
        data = views.format_component_wiki_pages(node=self.project, auth=self.consolidate_auth)
        self.asserEqual(data, expected)

    @mock.patch('addons.wiki.tasks.run_project_wiki_validate_for_import.delay')
    def test_project_wiki_validate_for_import(self,mock_delay):
        mock_delay.return_value = {'id':'id'}

        res = views.project_wiki_validate_for_import()
        self.asserEqual(res, 'id')

    def test_project_wiki_validate_for_import_process(self):
        result = views.project_wiki_validate_for_import_process(
            self.root_import_folder_validate._id,
            self.project)
        self.assertEqual(result['duplicated_folder'], [])
        self.assertTrue(result['canStartImport'])
        self.assertCountEqual(result['data'], [{'parent_wiki_name': 'importpage1', 'path': '/importpage1/importpage2', 'original_name': 'importpage2', 'wiki_name': 'importpage2', 'status': 'valid', 'message': '', '_id': self.import_page_md_file_2._id}, {'parent_wiki_name': None, 'path': '/importpage1', 'original_name': 'importpage1', 'wiki_name': 'importpage1', 'status': 'valid', 'message': '', '_id': self.import_page_md_file_1._id}])
 
    def test_validate_import_folder_invalid(self):
        folder = BaseFileNode.objects.get(name='importpagex')
        parent_path = ''
        result = views._validate_import_folder(self.project, folder, parent_path)
        for info in result:
            self.assertEqual(info['path'], '/importpagex')
            self.assertEqual(info['original_name'], 'importpagex')
            self.assertEqual(info['name'], 'importpagex')
            self.assertEqual(info['status'], 'invalid')
            self.assertEqual(info['message'], 'The wiki page does not exist, so the subordinate pages are not processed.')

    def test_validate_import_folder(self):
        folder = self.import_page_folder_1
        parent_path = ''
        result = views._validate_import_folder(self.project, folder, parent_path)
        expected_results = [
            {'parent_wiki_name': 'importpage1', 'path': '/importpage1/importpage2', 'original_name': 'importpage2', 'wiki_name': 'importpage2', 'status': 'valid', 'message': '', '_id': self.import_page_md_file_2._id},
            {'parent_wiki_name': None, 'path': '/importpage1', 'original_name': 'importpage1', 'wiki_name': 'importpage1', 'status': 'valid', 'message': '', '_id': self.import_page_md_file_1._id}
        ]
        for expected_result in expected_results:
            self.assertIn(expected_result, result)

    def test_validate_import_wiki_exists_duplicated_valid_exists_status_change(self):
        info = {'wiki_name': 'importpagea', 'path': '/importpagea', 'status': 'valid'}
        result, can_start_import = views._validate_import_wiki_exists_duplicated(self.project, info)
        self.assertEqual(result['status'], 'valid_exists')
        self.assertFalse(can_start_import)

    def test_validate_import_wiki_exists_duplicated_valid_duplicated_status_change(self):
        info = {'wiki_name': 'importpageb', 'path': '/importpagea/importpageb', 'status': 'valid'}
        result, can_start_import = views._validate_import_wiki_exists_duplicated(self.project, info)
        self.assertEqual(result['status'], 'valid_duplicated')
        self.assertFalse(can_start_import)

    def test_validate_import_duplicated_directry_no_duplicated(self):
        info_list = []
        result = views._validate_import_duplicated_directry(info_list)
        self.assertEqual(result, [])

    def test_validate_import_duplicated_directry_duplicated(self):
        info_list = [
            {'original_name': 'folder1'},
            {'original_name': 'folder2'},
            {'original_name': 'folder1'},
            {'original_name': 'folder3'}
        ]
        result = views._validate_import_duplicated_directry(info_list)
        self.assertEqual(result, ['folder1'])

    @mock.patch('addons.wiki.views.project_wiki_import_process')
    @mock.patch('addons.wiki.utils.check_file_object_in_node')
    def test_project_wiki_import(self, mock_check_file_object_in_node, mock_project_wiki_import_process):
        mock_check_file_object_in_node.return_value = True
        dir_id = self.root_import_folder1._id
        url = self.project.api_url_for('project_wiki_import', dir_id=dir_id)
        res = self.app.post_json(url, { 'data': [{'test': 'test1'}] }, auth=self.user.auth)
        response_json = res.json
        task_id = response_json['taskId']
        uuid_obj = uuid.UUID(task_id)
        self.assertIsNotNone(uuid_obj)

    @mock.patch('addons.wiki.views._get_md_content_from_wb')
    @mock.patch('addons.wiki.views._get_or_create_wiki_folder')
    @mock.patch('addons.wiki.views._create_wiki_folder')
    @mock.patch('addons.wiki.views._wiki_copy_import_directory')
    @mock.patch('addons.wiki.views._wiki_content_replace')
    @mock.patch('addons.wiki.views._wiki_import_create_or_update')
    @mock.patch('addons.wiki.views._import_same_level_wiki')
    @mock.patch('addons.wiki.tasks.run_update_search_and_bulk_index')
    def test_project_wiki_import_process(self, mock_run_task_elasticsearch, mock_import_same_level_wiki, mock_wiki_import_create_or_update, mock_wiki_content_replace, mock_wiki_copy_import_directory, mock_create_wiki_folder, mock_get_or_create_wiki_folder, mock_get_md_content_from_wb):
        # root
        # └── rootimportfolder2
        #     ├── importpage1
        #     │   ├── importpage1.md
        #     │   └── importpage2
        #     │       ├── importpage2.md
        #     │       └── importpage3
        #     │           └── importpage3.md
        #     └── importpage4
        #         ├── importpage4.md
        #         └── importpage5
        #             └── importpage5.md
        self.root_import_folder = TestFolder.objects.create(name='rootimportfolder', target=self.project, parent=self.root)
        self.import_page_folder_1 = TestFolder.objects.create(name='importpage1', target=self.project, parent=self.root_import_folder)
        self.import_page_md_file_1 = TestFile.objects.create(name='importpage1.md', target=self.project, parent=self.import_page_folder_1)
        self.import_page_folder_2 = TestFolder.objects.create(name='importpage2', target=self.project, parent=self.import_page_folder_1)
        self.import_page_md_file_2 = TestFile.objects.create(name='importpage2.md', target=self.project, parent=self.import_page_folder_2)
        self.import_page_folder_3 = TestFolder.objects.create(name='importpage3', target=self.project, parent=self.import_page_folder_2)
        self.import_page_md_file_3 = TestFile.objects.create(name='importpage3.md', target=self.project, parent=self.import_page_folder_3)
        self.import_page_folder_4 = TestFolder.objects.create(name='importpage4', target=self.project, parent=self.root_import_folder)
        self.import_page_md_file_4 = TestFile.objects.create(name='importpage4.md', target=self.project, parent=self.import_page_folder_4)
        self.import_page_folder_5 = TestFolder.objects.create(name='importpage5', target=self.project, parent=self.import_page_folder_4)
        self.import_page_md_file_5 = TestFile.objects.create(name='importpage5.md', target=self.project, parent=self.import_page_folder_5)
        mock_get_md_content_from_wb.return_value = [
            {
                'parent_wiki_name': None,
                'path': '/importpage4',
                'original_name': 'importpage4',
                'wiki_name': 'importpage4',
                'status': 'valid',
                'message': '',
                '_id': 'abc',
                'wiki_content': 'importpage4 content'
            },
            {
                'parent_wiki_name': 'importpage4',
                'path': '/importpage4/importpage5',
                'original_name': 'importpage5',
                'wiki_name': 'importpage5',
                'status': 'valid',
                'message': '',
                '_id': 'def',
                'wiki_content': 'importpage5 content'
            },
            {
                'parent_wiki_name': None,
                'path': '/importpage1',
                'original_name': 'importpage1',
                'wiki_name': 'importpage1',
                'status': 'valid',
                'message': '',
                '_id': 'ghi',
                'wiki_content': 'importpage1 content'
            },
            {
                'parent_wiki_name': 'importpage1',
                'path': '/importpage1/importpage2',
                'original_name': 'importpage2',
                'wiki_name': 'importpage2',
                'status': 'valid',
                'message': '',
                '_id': 'jkl',
                'wiki_content': 'importpage2 content'
            },
            {
                'parent_wiki_name': 'importpage2',
                'path': '/importpage1/importpage2/importpage3',
                'original_name': 'importpage3',
                'wiki_name': 'importpage3',
                'status': 'valid',
                'message': '',
                '_id': 'mno',
                'wiki_content': 'importpage3 content'
            }
        ]

        mock_get_or_create_wiki_folder.side_effect = [(123, 'osfstorage/wikiimage_id/'), (456, 'osfstorage/wikiimportedfolder_id/')]
        mock_create_wiki_folder.return_value = 789, 'osfstorage/wikisortedcopyfolder_id/'
        mock_wiki_copy_import_directory.return_value = 'clone_id'
        mock_wiki_content_replace.return_value = [
            {
                'parent_wiki_name': None,
                'path': '/importpage4',
                'original_name': 'importpage4',
                'wiki_name': 'importpage4',
                'status': 'valid',
                'message': '',
                '_id': 'abc',
                'wiki_content': 'importpage4 content'
            },
            {
                'parent_wiki_name': 'importpage4',
                'path': '/importpage4/importpage5',
                'original_name': 'importpage5',
                'wiki_name': 'importpage5',
                'status': 'valid',
                'message': '',
                '_id': 'def',
                'wiki_content': 'importpage5 content'
            },
            {
                'parent_wiki_name': None,
                'path': '/importpage1',
                'original_name': 'importpage1',
                'wiki_name': 'importpage1',
                'status': 'valid',
                'message': '',
                '_id': 'ghi',
                'wiki_content': 'importpage1 content'
            },
            {
                'parent_wiki_name': 'importpage1',
                'path': '/importpage1/importpage2',
                'original_name': 'importpage2',
                'wiki_name': 'importpage2',
                'status': 'valid',
                'message': '',
                '_id': 'jkl',
                'wiki_content': 'importpage2 content'
            },
            {
                'parent_wiki_name': 'importpage2',
                'path': '/importpage1/importpage2/importpage3',
                'original_name': 'importpage3',
                'wiki_name': 'importpage3',
                'status': 'valid',
                'message': '',
                '_id': 'mno',
                'wiki_content': 'importpage3 content'
            }
        ]

        mock_wiki_import_create_or_update.side_effect = [({'status': 'success', 'path': '/importpage4'}, 4), ({'status': 'success', 'path': '/importpage1'}, 1)]
        mock_import_same_level_wiki.side_effect = [([{'status': 'success', 'path': '/importpage4/importpage5'}, {'status': 'success', 'path': '/importpage1/importpage2'}], [5, 2]), ([{'status': 'success', 'path': '/importpage1/importpage2/importpage3'}], [3])]

        expected_result = {
            'ret': [
                {'status': 'success', 'path': '/importpage4'},
                {'status': 'success', 'path': '/importpage1'},
                {'status': 'success', 'path': '/importpage4/importpage5'},
                {'status': 'success', 'path': '/importpage1/importpage2'},
                {'status': 'success', 'path': '/importpage1/importpage2/importpage3'}
            ],
            'import_errors': []
        }

        result = views.project_wiki_import_process(self.data, self.root_import_folder._id, 'task_id', self.consolidate_auth, self.project)
        self.assertEqual(result, expected_result)
        mock_run_task_elasticsearch.delay.assert_called_once_with(self.project.guids.first()._id, [4, 1, 5, 2, 3])
        task = WikiImportTask.objects.get(task_id='task_id')
        self.assertEqual(task.status, task.STATUS_COMPLETED)

    @mock.patch('addons.wiki.views._get_md_content_from_wb')
    @mock.patch('addons.wiki.views._get_or_create_wiki_folder')
    @mock.patch('addons.wiki.views._create_wiki_folder')
    @mock.patch('addons.wiki.views._wiki_copy_import_directory')
    @mock.patch('addons.wiki.views._wiki_content_replace')
    @mock.patch('addons.wiki.views._wiki_import_create_or_update')
    @mock.patch('addons.wiki.tasks.run_update_search_and_bulk_index')
    @mock.patch('addons.wiki.views.set_wiki_import_task_proces_end')
    def test_project_wiki_import_process_top_level_aborted(self, mock_wiki_import_task_prcess_end, mock_run_task_elasticsearch, mock_wiki_import_create_or_update, mock_wiki_content_replace, mock_wiki_copy_import_directory, mock_create_wiki_folder, mock_get_or_create_wiki_folder, mock_get_md_content_from_wb):
        self.root_import_folder = TestFolder.objects.create(name='rootimportfolder', target=self.project, parent=self.root)
        mock_get_md_content_from_wb.return_value = [
            {
                'parent_wiki_name': None,
                'path': '/importpage4',
                'original_name': 'importpage4',
                'wiki_name': 'importpage4',
                'status': 'valid',
                'message': '',
                '_id': 'abc',
                'wiki_content': 'importpage4 content'
            },
            {
                'parent_wiki_name': 'importpage4',
                'path': '/importpage4/importpage5',
                'original_name': 'importpage5',
                'wiki_name': 'importpage5',
                'status': 'valid',
                'message': '',
                '_id': 'def',
                'wiki_content': 'importpage5 content'
            },
            {
                'parent_wiki_name': None,
                'path': '/importpage1',
                'original_name': 'importpage1',
                'wiki_name': 'importpage1',
                'status': 'valid',
                'message': '',
                '_id': 'ghi',
                'wiki_content': 'importpage1 content'
            },
            {
                'parent_wiki_name': 'importpage1',
                'path': '/importpage1/importpage2',
                'original_name': 'importpage2',
                'wiki_name': 'importpage2',
                'status': 'valid',
                'message': '',
                '_id': 'jkl',
                'wiki_content': 'importpage2 content'
            },
            {
                'parent_wiki_name': 'importpage2',
                'path': '/importpage1/importpage2/importpage3',
                'original_name': 'importpage3',
                'wiki_name': 'importpage3',
                'status': 'valid',
                'message': '',
                '_id': 'mno',
                'wiki_content': 'importpage3 content'
            }
        ]

        mock_get_or_create_wiki_folder.side_effect = [(123, 'osfstorage/wikiimage_id/'), (456, 'osfstorage/wikiimportedfolder_id/')]
        mock_create_wiki_folder.return_value = 789, 'osfstorage/wikisortedcopyfolder_id/'
        mock_wiki_copy_import_directory.return_value = 'clone_id'
        mock_wiki_content_replace.return_value = [
            {
                'parent_wiki_name': None,
                'path': '/importpage4',
                'original_name': 'importpage4',
                'wiki_name': 'importpage4',
                'status': 'valid',
                'message': '',
                '_id': 'abc',
                'wiki_content': 'importpage4 content'
            },
            {
                'parent_wiki_name': 'importpage4',
                'path': '/importpage4/importpage5',
                'original_name': 'importpage5',
                'wiki_name': 'importpage5',
                'status': 'valid',
                'message': '',
                '_id': 'def',
                'wiki_content': 'importpage5 content'
            },
            {
                'parent_wiki_name': None,
                'path': '/importpage1',
                'original_name': 'importpage1',
                'wiki_name': 'importpage1',
                'status': 'valid',
                'message': '',
                '_id': 'ghi',
                'wiki_content': 'importpage1 content'
            },
            {
                'parent_wiki_name': 'importpage1',
                'path': '/importpage1/importpage2',
                'original_name': 'importpage2',
                'wiki_name': 'importpage2',
                'status': 'valid',
                'message': '',
                '_id': 'jkl',
                'wiki_content': 'importpage2 content'
            },
            {
                'parent_wiki_name': 'importpage2',
                'path': '/importpage1/importpage2/importpage3',
                'original_name': 'importpage3',
                'wiki_name': 'importpage3',
                'status': 'valid',
                'message': '',
                '_id': 'mno',
                'wiki_content': 'importpage3 content'
            }
        ]

        mock_wiki_import_create_or_update.side_effect = views.ImportTaskAbortedError

        expected_result = {'aborted': True}

        result = views.project_wiki_import_process(self.data, self.root_import_folder._id, 'task_id', self.consolidate_auth, self.project)
        self.assertEqual(result, expected_result)
        mock_run_task_elasticsearch.delay.assert_called_once_with(self.project.guids.first()._id, [])
        mock_wiki_import_task_prcess_end.assert_called_once_with(self.project)

    @mock.patch('addons.wiki.views._get_md_content_from_wb')
    @mock.patch('addons.wiki.views._get_or_create_wiki_folder')
    @mock.patch('addons.wiki.views._create_wiki_folder')
    @mock.patch('addons.wiki.views._wiki_copy_import_directory')
    @mock.patch('addons.wiki.views._wiki_content_replace')
    @mock.patch('addons.wiki.views._wiki_import_create_or_update')
    @mock.patch('addons.wiki.views._import_same_level_wiki')
    @mock.patch('addons.wiki.tasks.run_update_search_and_bulk_index')
    @mock.patch('addons.wiki.views.set_wiki_import_task_proces_end')
    def test_project_wiki_import_process_sub_level_aborted(self, mock_wiki_import_task_prcess_end, mock_run_task_elasticsearch, mock_import_same_level_wiki, mock_wiki_import_create_or_update, mock_wiki_content_replace, mock_wiki_copy_import_directory, mock_create_wiki_folder, mock_get_or_create_wiki_folder, mock_get_md_content_from_wb):
        self.root_import_folder = TestFolder.objects.create(name='rootimportfolder', target=self.project, parent=self.root)
        mock_get_md_content_from_wb.return_value = [
            {
                'parent_wiki_name': None,
                'path': '/importpage4',
                'original_name': 'importpage4',
                'wiki_name': 'importpage4',
                'status': 'valid',
                'message': '',
                '_id': 'abc',
                'wiki_content': 'importpage4 content'
            },
            {
                'parent_wiki_name': 'importpage4',
                'path': '/importpage4/importpage5',
                'original_name': 'importpage5',
                'wiki_name': 'importpage5',
                'status': 'valid',
                'message': '',
                '_id': 'def',
                'wiki_content': 'importpage5 content'
            },
            {
                'parent_wiki_name': None,
                'path': '/importpage1',
                'original_name': 'importpage1',
                'wiki_name': 'importpage1',
                'status': 'valid',
                'message': '',
                '_id': 'ghi',
                'wiki_content': 'importpage1 content'
            },
            {
                'parent_wiki_name': 'importpage1',
                'path': '/importpage1/importpage2',
                'original_name': 'importpage2',
                'wiki_name': 'importpage2',
                'status': 'valid',
                'message': '',
                '_id': 'jkl',
                'wiki_content': 'importpage2 content'
            },
            {
                'parent_wiki_name': 'importpage2',
                'path': '/importpage1/importpage2/importpage3',
                'original_name': 'importpage3',
                'wiki_name': 'importpage3',
                'status': 'valid',
                'message': '',
                '_id': 'mno',
                'wiki_content': 'importpage3 content'
            }
        ]

        mock_get_or_create_wiki_folder.side_effect = [(123, 'osfstorage/wikiimage_id/'), (456, 'osfstorage/wikiimportedfolder_id/')]
        mock_create_wiki_folder.return_value = 789, 'osfstorage/wikisortedcopyfolder_id/'
        mock_wiki_copy_import_directory.return_value = 'clone_id'
        mock_wiki_content_replace.return_value = [
            {
                'parent_wiki_name': None,
                'path': '/importpage4',
                'original_name': 'importpage4',
                'wiki_name': 'importpage4',
                'status': 'valid',
                'message': '',
                '_id': 'abc',
                'wiki_content': 'importpage4 content'
            },
            {
                'parent_wiki_name': 'importpage4',
                'path': '/importpage4/importpage5',
                'original_name': 'importpage5',
                'wiki_name': 'importpage5',
                'status': 'valid',
                'message': '',
                '_id': 'def',
                'wiki_content': 'importpage5 content'
            },
            {
                'parent_wiki_name': None,
                'path': '/importpage1',
                'original_name': 'importpage1',
                'wiki_name': 'importpage1',
                'status': 'valid',
                'message': '',
                '_id': 'ghi',
                'wiki_content': 'importpage1 content'
            },
            {
                'parent_wiki_name': 'importpage1',
                'path': '/importpage1/importpage2',
                'original_name': 'importpage2',
                'wiki_name': 'importpage2',
                'status': 'valid',
                'message': '',
                '_id': 'jkl',
                'wiki_content': 'importpage2 content'
            },
            {
                'parent_wiki_name': 'importpage2',
                'path': '/importpage1/importpage2/importpage3',
                'original_name': 'importpage3',
                'wiki_name': 'importpage3',
                'status': 'valid',
                'message': '',
                '_id': 'mno',
                'wiki_content': 'importpage3 content'
            }
        ]

        mock_wiki_import_create_or_update.side_effect = [({'status': 'success', 'path': '/importpage4'}, 4), ({'status': 'success', 'path': '/importpage1'}, 1)]
        mock_import_same_level_wiki.side_effect = ImportTaskAbortedError

        expected_result = {'aborted': True}

        result = views.project_wiki_import_process(self.data, self.root_import_folder._id, 'task_id', self.consolidate_auth, self.project)
        self.assertEqual(result, expected_result)
        mock_run_task_elasticsearch.delay.assert_called_once_with(self.project.guids.first()._id, [4, 1])
        mock_wiki_import_task_prcess_end.assert_called_once_with(self.project)

    @mock.patch('addons.wiki.views._get_md_content_from_wb')
    def test_project_wiki_import_process_wb_aborted(self, mock_get_md_content_from_wb):
        self.root_import_folder = TestFolder.objects.create(name='rootimportfolder', target=self.project, parent=self.root)
        mock_get_md_content_from_wb.return_value = None
        expected_result = {'aborted': True}
        result = views.project_wiki_import_process(self.data, self.root_import_folder._id, 'task_id', self.consolidate_auth, self.project)
        self.assertEqual(result, expected_result)

    @mock.patch('addons.wiki.views._get_md_content_from_wb')
    @mock.patch('addons.wiki.views._get_or_create_wiki_folder')
    @mock.patch('addons.wiki.views._create_wiki_folder')
    @mock.patch('addons.wiki.views._wiki_copy_import_directory')
    @mock.patch('addons.wiki.views._wiki_content_replace')
    def test_project_wiki_import_process_replace_aborted(self, mock_wiki_content_replace, mock_wiki_copy_import_directory, mock_create_wiki_folder, mock_get_or_create_wiki_folder, mock_get_md_content_from_wb):
        self.root_import_folder = TestFolder.objects.create(name='rootimportfolder', target=self.project, parent=self.root)
        self.root_import_folder = TestFolder.objects.create(name='rootimportfolder', target=self.project, parent=self.root)
        mock_get_md_content_from_wb.return_value = [
            {
                'parent_wiki_name': None,
                'path': '/importpage4',
                'original_name': 'importpage4',
                'wiki_name': 'importpage4',
                'status': 'valid',
                'message': '',
                '_id': 'abc',
                'wiki_content': 'importpage4 content'
            },
            {
                'parent_wiki_name': 'importpage4',
                'path': '/importpage4/importpage5',
                'original_name': 'importpage5',
                'wiki_name': 'importpage5',
                'status': 'valid',
                'message': '',
                '_id': 'def',
                'wiki_content': 'importpage5 content'
            },
            {
                'parent_wiki_name': None,
                'path': '/importpage1',
                'original_name': 'importpage1',
                'wiki_name': 'importpage1',
                'status': 'valid',
                'message': '',
                '_id': 'ghi',
                'wiki_content': 'importpage1 content'
            },
            {
                'parent_wiki_name': 'importpage1',
                'path': '/importpage1/importpage2',
                'original_name': 'importpage2',
                'wiki_name': 'importpage2',
                'status': 'valid',
                'message': '',
                '_id': 'jkl',
                'wiki_content': 'importpage2 content'
            },
            {
                'parent_wiki_name': 'importpage2',
                'path': '/importpage1/importpage2/importpage3',
                'original_name': 'importpage3',
                'wiki_name': 'importpage3',
                'status': 'valid',
                'message': '',
                '_id': 'mno',
                'wiki_content': 'importpage3 content'
            }
        ]

        mock_get_or_create_wiki_folder.side_effect = [(123, 'osfstorage/wikiimage_id/'), (456, 'osfstorage/wikiimportedfolder_id/')]
        mock_create_wiki_folder.return_value = 789, 'osfstorage/wikisortedcopyfolder_id/'
        mock_wiki_copy_import_directory.return_value = 'clone_id'
        mock_wiki_content_replace.return_value = None
        expected_result = {'aborted': True}
        result = views.project_wiki_import_process(self.data, self.root_import_folder._id, 'task_id', self.consolidate_auth, self.project)
        self.assertEqual(result, expected_result)

    def test_replace_wiki_link_notation_wiki_page_with_tooptip(self):
        wiki_content_link = 'Wiki content with [wiki page1](wiki%20page1 "tooltip1")'
        link_matches = list(re.finditer(self.rep_link, wiki_content_link))
        info = self.wiki_info
        import_wiki_name_list = ['importpage1', 'importpage2']
        expected_content = f'Wiki content with [wiki page1](../wiki%20page1/ "tooltip1")'
        result_content = views._replace_wiki_link_notation(self.project, link_matches, wiki_content_link, info, self.node_file_mapping, import_wiki_name_list, self.root_import_folder1._id)
        self.assertEqual(result_content, expected_content)

    def test_replace_wiki_link_notation_wiki_page_without_tooptip(self):
        wiki_content_link = 'Wiki content with [wiki page1](wiki%20page1)'
        link_matches = list(re.finditer(self.rep_link, wiki_content_link))
        info = self.wiki_info
        import_wiki_name_list = ['importpage1', 'importpage2']
        expected_content = f'Wiki content with [wiki page1](../wiki%20page1/)'
        result_content = views._replace_wiki_link_notation(self.project, link_matches, wiki_content_link, info, self.node_file_mapping, import_wiki_name_list, self.root_import_folder1._id)
        self.assertEqual(result_content, expected_content)

    def test_replace_wiki_link_notation_attachment_file(self):
        wiki_content_link_attachment = 'Wiki content with [attachment1.doc](attachment1.doc)'
        link_matches = list(re.finditer(self.rep_link, wiki_content_link_attachment))
        info = self.wiki_info
        import_wiki_name_list = ['importpage1', 'importpage2']
        expected_content = f'Wiki content with [attachment1.doc]({website_settings.DOMAIN}{self.guid}/files/osfstorage/{self.import_attachment1_doc._id})'
        result_content = views._replace_wiki_link_notation(self.project, link_matches, wiki_content_link_attachment, info, self.node_file_mapping, import_wiki_name_list, self.root_import_folder1._id)
        self.assertEqual(result_content, expected_content)

    def test_replace_wiki_link_notation_has_slash(self):
        wiki_content_link_has_slash = 'Wiki content with [wiki/page](wiki/page)'
        link_matches = list(re.finditer(self.rep_link, wiki_content_link_has_slash))
        info = self.wiki_info
        import_wiki_name_list = ['importpage1', 'importpage2']
        expected_content = wiki_content_link_has_slash
        result_content = views._replace_wiki_link_notation(self.project, link_matches, wiki_content_link_has_slash, info, self.node_file_mapping, import_wiki_name_list, self.root_import_folder1._id)
        self.assertEqual(result_content, expected_content)

    def test_replace_wiki_link_notation_has_sharp_and_is_wiki_with_tooltip(self):
        wiki_content_link = 'Wiki content with [importpage1#anchor](importpage1#anchor "tooltip text")'
        link_matches = list(re.finditer(self.rep_link, wiki_content_link))
        info = self.wiki_info
        import_wiki_name_list = ['importpage1', 'importpage2']
        expected_content = 'Wiki content with [importpage1#anchor](../importpage1/#anchor "tooltip text")'
        result_content = views._replace_wiki_link_notation(self.project, link_matches, wiki_content_link, info, self.node_file_mapping, import_wiki_name_list, self.root_import_folder1._id)
        self.assertEqual(result_content, expected_content)

    def test_replace_wiki_link_notation_has_sharp_and_is_wiki_without_tooltip(self):
        wiki_content_link = 'Wiki content with [importpage1#anchor](importpage1#anchor)'
        link_matches = list(re.finditer(self.rep_link, wiki_content_link))
        info = self.wiki_info
        import_wiki_name_list = ['importpage1', 'importpage2']
        expected_content = 'Wiki content with [importpage1#anchor](../importpage1/#anchor)'
        result_content = views._replace_wiki_link_notation(self.project, link_matches, wiki_content_link, info, self.node_file_mapping, import_wiki_name_list, self.root_import_folder1._id)
        self.assertEqual(result_content, expected_content)

    def test_replace_wiki_link_notation_is_url(self):
        wiki_content_link_is_url = 'Wiki content with [example](https://example.com)'
        link_matches = list(re.finditer(self.rep_link, wiki_content_link_is_url))
        info = self.wiki_info
        import_wiki_name_list = ['importpage1', 'importpage2']
        expected_content = wiki_content_link_is_url
        result_content = views._replace_wiki_link_notation(self.project, link_matches, wiki_content_link_is_url, info, self.node_file_mapping, import_wiki_name_list, self.root_import_folder1._id)
        self.assertEqual(result_content, expected_content)

    def test_replace_wiki_link_notation_no_link(self):
        wiki_content = 'Wiki content'
        link_matches = list(re.finditer(self.rep_link, wiki_content))
        info = self.wiki_info
        import_wiki_name_list = ['importpage1', 'importpage2']
        expected_content = wiki_content
        result_content = views._replace_wiki_link_notation(self.project, link_matches, wiki_content, info, self.node_file_mapping, import_wiki_name_list, self.root_import_folder1._id)
        self.assertEqual(result_content, expected_content)

    def test_check_wiki_name_exist_existing_wiki(self):
        wiki_name = 'wiki%20page1'
        import_wiki_name_list = ['importpage1', 'importpage2']
        result_content = views._check_wiki_name_exist(self.project, wiki_name, self.node_file_mapping, import_wiki_name_list)
        self.assertTrue(result_content)

    def test_check_wiki_name_exist_import_directory(self):
        wiki_name = 'importpage1'
        import_wiki_name_list = ['importpage1', 'importpage2']
        result_content = views._check_wiki_name_exist(self.project, wiki_name, self.node_file_mapping, import_wiki_name_list)
        self.assertTrue(result_content)

    def test_check_wiki_name_exist_not_existing(self):
        wiki_name = 'not%20existing%20wiki'
        import_wiki_name_list = ['importpage1', 'importpage2']
        result_content = views._check_wiki_name_exist(self.project, wiki_name, self.node_file_mapping, import_wiki_name_list)
        self.assertFalse(result_content)

    def test_check_wiki_name_exist_existing_wiki_nfd(self):
        wiki_name = 'wiki%20page1'
        wiki_name_nfd = unicodedata.normalize('NFD', wiki_name)
        import_wiki_name_list = ['importpage1', 'importpage2']
        result_content = views._check_wiki_name_exist(self.project, wiki_name_nfd, self.node_file_mapping, import_wiki_name_list)
        self.assertTrue(result_content)


    def test_replace_file_name_image_with_tooltip(self):
        wiki_name = self.import_page_folder1.name
        wiki_content_image_tooltip = 'Wiki content with ![](image1.png "tooltip1")'
        match = list(re.finditer(self.rep_image, wiki_content_image_tooltip))[0]
        notation = 'image'
        match_path, tooltip_match = views._exclude_tooltip(match['path'])
        expected_content = f'Wiki content with ![](<{website_settings.WATERBUTLER_URL}/v1/resources/{self.guid}/providers/osfstorage/{self.import_attachment_image1._id}?mode=render> "tooltip1")'
        result = views._replace_file_name(self.project, wiki_name, wiki_content_image_tooltip, match, notation, self.root_import_folder1._id, match_path, tooltip_match, self.node_file_mapping)
        self.assertEqual(result, expected_content)

    def test_replace_file_name_image_without_tooltip(self):
        wiki_name = self.import_page_folder1.name
        wiki_content_image_tooltip = 'Wiki content with ![](image1.png)'
        match = list(re.finditer(self.rep_image, wiki_content_image_tooltip))[0]
        notation = 'image'
        match_path, tooltip_match = views._exclude_tooltip(match['path'])
        expected_content = f'Wiki content with ![]({website_settings.WATERBUTLER_URL}/v1/resources/{self.guid}/providers/osfstorage/{self.import_attachment_image1._id}?mode=render)'
        result = views._replace_file_name(self.project, wiki_name, wiki_content_image_tooltip, match, notation, self.root_import_folder1._id, match_path, tooltip_match, self.node_file_mapping)
        self.assertEqual(result, expected_content)

    def test_replace_file_name_image_with_size_with_tooltip(self):
        wiki_name = self.import_page_folder1.name
        wiki_content_image_tooltip = 'Wiki content with ![](image1.png "tooltip2" =200)'
        match = list(re.finditer(self.rep_image, wiki_content_image_tooltip))[0]
        notation = 'image'
        match_path, tooltip_match = views._exclude_tooltip(match['path'])
        expected_content = f'Wiki content with ![](<{website_settings.WATERBUTLER_URL}/v1/resources/{self.guid}/providers/osfstorage/{self.import_attachment_image1._id}?mode=render =200> "tooltip2")'
        result = views._replace_file_name(self.project, wiki_name, wiki_content_image_tooltip, match, notation, self.root_import_folder1._id, match_path, tooltip_match, self.node_file_mapping)
        self.assertEqual(result, expected_content)

    def test_replace_file_name_image_with_size_without_tooltip(self):
        wiki_name = self.import_page_folder1.name
        wiki_content_image_tooltip = 'Wiki content with ![](image1.png =200)'
        match = list(re.finditer(self.rep_image, wiki_content_image_tooltip))[0]
        notation = 'image'
        match_path, tooltip_match = views._exclude_tooltip(match['path'])
        expected_content = f'Wiki content with ![]({website_settings.WATERBUTLER_URL}/v1/resources/{self.guid}/providers/osfstorage/{self.import_attachment_image1._id}?mode=render =200)'
        result = views._replace_file_name(self.project, wiki_name, wiki_content_image_tooltip, match, notation, self.root_import_folder1._id, match_path, tooltip_match, self.node_file_mapping)
        self.assertEqual(result, expected_content)

    def test_replace_file_name_image_with_invalid_size_with_tooltip(self):
        wiki_name = self.import_page_folder1.name
        wiki_content_image_tooltip = 'Wiki content with ![](image1.png "tooltip" =abcde)'
        match = list(re.finditer(self.rep_image, wiki_content_image_tooltip))[0]
        notation = 'image'
        match_path, tooltip_match = views._exclude_tooltip(match['path'])
        expected_content = wiki_content_image_tooltip
        result = views._replace_file_name(self.project, wiki_name, wiki_content_image_tooltip, match, notation, self.root_import_folder1._id, match_path, tooltip_match, self.node_file_mapping)
        self.assertEqual(result, expected_content)

    def test_replace_file_name_image_with_invalid_size_without_tooltip(self):
        wiki_name = self.import_page_folder1.name
        wiki_content_image_tooltip = 'Wiki content with ![](image1.png =abcde)'
        match = list(re.finditer(self.rep_image, wiki_content_image_tooltip))[0]
        notation = 'image'
        match_path, tooltip_match = views._exclude_tooltip(match['path'])
        expected_content = wiki_content_image_tooltip
        result = views._replace_file_name(self.project, wiki_name, wiki_content_image_tooltip, match, notation, self.root_import_folder1._id, match_path, tooltip_match, self.node_file_mapping)
        self.assertEqual(result, expected_content)

    def test_replace_file_name_link_with_tooltip(self):
        wiki_name = self.import_page_folder1.name
        wiki_content_link_tooltip = 'Wiki content with [attachment1.doc](attachment1.doc "tooltip1")'
        match = list(re.finditer(self.rep_link, wiki_content_link_tooltip))[0]
        notation = 'link'
        match_path, tooltip_match = views._exclude_tooltip(match['path'])
        expected_content = f'Wiki content with [attachment1.doc]({website_settings.DOMAIN}{self.guid}/files/osfstorage/{self.import_attachment1_doc._id} "tooltip1")'
        result = views._replace_file_name(self.project, wiki_name, wiki_content_link_tooltip, match, notation, self.root_import_folder1._id, match_path, tooltip_match, self.node_file_mapping)
        self.assertEqual(result, expected_content)

    def test_replace_file_name_link_without_tooltip(self):
        wiki_name = self.import_page_folder1.name
        wiki_content_link_tooltip = 'Wiki content with [attachment1.doc](attachment1.doc)'
        match = list(re.finditer(self.rep_link, wiki_content_link_tooltip))[0]
        notation = 'link'
        match_path, tooltip_match = views._exclude_tooltip(match['path'])
        expected_content = f'Wiki content with [attachment1.doc]({website_settings.DOMAIN}{self.guid}/files/osfstorage/{self.import_attachment1_doc._id})'
        result = views._replace_file_name(self.project, wiki_name, wiki_content_link_tooltip, match, notation, self.root_import_folder1._id, match_path, tooltip_match, self.node_file_mapping)
        self.assertEqual(result, expected_content)