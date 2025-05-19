from django.db.models import functions as functions

from osf_tests.factories import (
    UserFactory, NodeFactory, ProjectFactory,
    AuthUserFactory, RegistrationFactory
)
from framework.auth import Auth
from addons.wiki.models import WikiImportTask, WikiPage, WikiVersion, render_content
from addons.wiki.utils import (
    get_sharejs_uuid, generate_private_uuid, share_db, delete_share_doc,
    migrate_uuid, format_wiki_version, serialize_wiki_settings, serialize_wiki_widget,
    check_file_object_in_node
)

@pytest.mark.enable_bookmark_creation
class TestWikiModels(OsfTestCase):

    def setUp(self):
        super(TestWikiModels, self).setUp()

    def test_save_import_false(self, *args, **kwargs):
        current_content = self.wiki_page.save(self.project)
        #self.wiki_page.node = 
        rv = WikiPage.save(self, False ,*args, **kwargs)
        mock_check_file_object_in_node.return_value = True
        dir_id = self.root_import_folder1._id
        url = self.project.api_url_for('project_wiki_validate_for_import', dir_id=dir_id)
        res = self.app.get(url)
        response_json = res.json
        task_id = response_json['taskId']
        uuid_obj = uuid.UUID(task_id)
        assert uuid_obj

    def test_format_project_wiki_pages_contributor(self):
        home_page = WikiPage.objects.create_for_node(self.project, 'home', 'content here', self.consolidate_auth,None,False)
        zoo_page = WikiPage.objects.create_for_node(self.project, 'zoo', 'koala', self.consolidate_auth,None,True)
        data = views.format_project_wiki_pages(self.project, self.consolidate_auth)
        expected = [
            {
                'page': {
                    'url': self.project.web_url_for('project_wiki_view', wname='home', _guid=True),
                    'name': 'Home',
                    'id': home_page._primary_key,
                }
            },
            {
                'page': {
                    'url': self.project.web_url_for('project_wiki_view', wname='zoo', _guid=True),
                    'name': 'zoo',
                    'sort_order': None,
                    'id': zoo_page._primary_key,
                },
                'children': [],
            }
        ]
        assert_equal(data, expected)

    def test_get_for_child_nodes(self):
        wiki = WikiPage.objects.get_for_child_nodes(self.project,'home')
        
        assert_equal(wiki, None)

    def test_get_wiki_pages_latest(self):
        wiki = WikiPage.objects.get_wiki_pages_latest(self.project,'home')
        
        wikiRtn = WikiVersion.objects.annotate(name=F('wiki_page__page_name'), newest_version=Max('wiki_page__versions__identifier')).filter(identifier=F('newest_version'), wiki_page__id__in=wiki_page_ids, wiki_page__parent__isnull=True)

        assert_equal(wiki, wikiRtn)