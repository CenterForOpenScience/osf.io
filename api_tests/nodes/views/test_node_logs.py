import mock
import pytest
import time

from dateutil.parser import parse as parse_date

from api.base.settings.defaults import API_BASE
from tests.base import ApiTestCase
from framework.auth.core import Auth
from osf.models import ProjectStorageType, QuickFilesNode
from osf_tests.factories import (
    AuthUserFactory,
    ProjectFactory,
    OSFGroupFactory,
    RegistrationFactory,
    EmbargoFactory,
    InstitutionFactory,
    RegionFactory,
)
from osf.utils.permissions import READ
from tests.base import assert_datetime_equal
from api_tests.utils import disconnected_from_listeners
from website.project.signals import contributor_removed

API_LATEST = 0
API_FIRST = -1


@pytest.fixture()
def user():
    return AuthUserFactory()


@pytest.mark.django_db
class TestNodeLogList:

    @pytest.fixture()
    def contrib(self):
        return AuthUserFactory()

    @pytest.fixture()
    def non_contrib(self):
        return AuthUserFactory()

    @pytest.fixture()
    def user_auth(self, user):
        return Auth(user)

    @pytest.fixture()
    def NodeLogFactory(self):
        return ProjectFactory()

    @pytest.fixture()
    def pointer(self, user):
        return ProjectFactory(creator=user)

    @pytest.fixture()
    def pointer_registration(self, user):
        return RegistrationFactory(creator=user, is_public=True)

    @pytest.fixture()
    def pointer_embargo(self, user):
        return RegistrationFactory(
            creator=user,
            embargo=EmbargoFactory(user=user),
            is_public=False)

    @pytest.fixture()
    def private_project(self, user):
        return ProjectFactory(is_public=False, creator=user)

    @pytest.fixture()
    def private_url(self, private_project):
        return '/{}nodes/{}/logs/?version=2.2'.format(
            API_BASE, private_project._id)

    @pytest.fixture()
    def public_project(self, user):
        return ProjectFactory(is_public=True, creator=user)

    @pytest.fixture()
    def public_url(self, public_project):
        return '/{}nodes/{}/logs/?version=2.2'.format(
            API_BASE, public_project._id)

    def test_can_view_osf_group_log(self, app, private_project, private_url):
        group_mem = AuthUserFactory()
        group = OSFGroupFactory(creator=group_mem)
        private_project.add_osf_group(group, READ)
        res = app.get(private_url, auth=group_mem.auth)
        assert res.status_code == 200

    def test_add_tag(self, app, user, user_auth, public_project, public_url):
        public_project.add_tag('Rheisen', auth=user_auth)
        assert public_project.logs.latest().action == 'tag_added'
        res = app.get(public_url, auth=user.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == public_project.logs.count()
        assert res.json['data'][API_LATEST]['attributes']['action'] == 'tag_added'
        assert 'Rheisen' == public_project.logs.latest().params['tag']

    def test_remove_tag(
            self, app, user, user_auth,
            public_project, public_url):
        public_project.add_tag('Rheisen', auth=user_auth)
        assert public_project.logs.latest().action == 'tag_added'
        public_project.remove_tag('Rheisen', auth=user_auth)
        assert public_project.logs.latest().action == 'tag_removed'
        res = app.get(public_url, auth=user)
        assert res.status_code == 200
        assert len(res.json['data']) == public_project.logs.count()
        assert res.json['data'][API_LATEST]['attributes']['action'] == 'tag_removed'
        assert public_project.logs.latest().params['tag'] == 'Rheisen'

    def test_project_creation(
            self, app, user, public_project, private_project,
            public_url, private_url):

        #   test_project_created
        res = app.get(public_url)
        assert res.status_code == 200
        assert len(res.json['data']) == public_project.logs.count()
        assert public_project.logs.first().action == 'project_created'
        assert public_project.logs.first(
        ).action == res.json['data'][API_LATEST]['attributes']['action']

    #   test_log_create_on_public_project
        res = app.get(public_url)
        assert res.status_code == 200
        assert len(res.json['data']) == public_project.logs.count()
        assert_datetime_equal(
            parse_date(
                res.json['data'][API_FIRST]['attributes']['date']),
            public_project.logs.first().date)
        assert res.json['data'][API_FIRST]['attributes']['action'] == public_project.logs.first(
        ).action

    #   test_log_create_on_private_project
        res = app.get(private_url, auth=user.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == public_project.logs.count()
        assert_datetime_equal(
            parse_date(
                res.json['data'][API_FIRST]['attributes']['date']),
            private_project.logs.first().date)
        assert res.json['data'][API_FIRST]['attributes']['action'] == private_project.logs.first(
        ).action

    def test_add_addon(self, app, user, user_auth, public_project, public_url):
        public_project.add_addon('github', auth=user_auth)
        assert public_project.logs.latest().action == 'addon_added'
        res = app.get(public_url, auth=user.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == public_project.logs.count()
        assert res.json['data'][API_LATEST]['attributes']['action'] == 'addon_added'

    def test_project_add_remove_contributor(
            self, app, user, contrib, user_auth,
            public_project, public_url):
        public_project.add_contributor(contrib, auth=user_auth)
        assert public_project.logs.latest().action == 'contributor_added'
        # Disconnect contributor_removed so that we don't check in files
        # We can remove this when StoredFileNode is implemented in osf-models
        with disconnected_from_listeners(contributor_removed):
            public_project.remove_contributor(contrib, auth=user_auth)
        assert public_project.logs.latest().action == 'contributor_removed'
        res = app.get(public_url, auth=user.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == public_project.logs.count()
        assert res.json['data'][API_LATEST]['attributes']['action'] == 'contributor_removed'
        assert res.json['data'][1]['attributes']['action'] == 'contributor_added'

    def test_remove_addon(
            self, app, user, user_auth,
            public_project, public_url):
        public_project.add_addon('github', auth=user_auth)
        assert public_project.logs.latest().action == 'addon_added'
        old_log_length = len(list(public_project.logs.all()))
        public_project.delete_addon('github', auth=user_auth)
        assert public_project.logs.latest().action == 'addon_removed'
        assert (public_project.logs.count() - 1) == old_log_length
        res = app.get(public_url, auth=user.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == public_project.logs.count()
        assert res.json['data'][API_LATEST]['attributes']['action'] == 'addon_removed'

    def test_pointers(
            self, app, user, user_auth, contrib,
            public_project, pointer, public_url):
        public_project.add_pointer(pointer, auth=user_auth, save=True)
        assert public_project.logs.latest().action == 'pointer_created'
        res = app.get(public_url, auth=user.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == public_project.logs.count()
        assert res.json['data'][API_LATEST]['attributes']['action'] == 'pointer_created'

        # Confirm pointer contains correct data for creator
        assert res.json['data'][API_LATEST]['attributes']['params']['pointer']['id'] == pointer._id

        res = app.get(public_url)
        assert res.status_code == 200
        assert res.json['data'][API_LATEST]['attributes']['params']['pointer'] is None

        res = app.get(public_url, auth=contrib.auth)
        assert res.status_code == 200
        assert res.json['data'][API_LATEST]['attributes']['params']['pointer'] is None

        # Make pointer public and check data
        pointer.is_public = True
        pointer.save()

        res = app.get(public_url, auth=user.auth)
        assert res.status_code == 200
        assert res.json['data'][API_LATEST]['attributes']['params']['pointer']['id'] == pointer._id

        res = app.get(public_url)
        assert res.status_code == 200
        assert res.json['data'][API_LATEST]['attributes']['params']['pointer']['id'] == pointer._id

        res = app.get(public_url, auth=contrib.auth)
        assert res.status_code == 200
        assert res.json['data'][API_LATEST]['attributes']['params']['pointer']['id'] == pointer._id

        # Delete pointer and make sure no data shown
        pointer.remove_node(Auth(user))

        res = app.get(public_url, auth=user.auth)
        assert res.status_code == 200
        assert res.json['data'][API_LATEST]['attributes']['params']['pointer'] is None

        res = app.get(public_url)
        assert res.status_code == 200
        assert res.json['data'][API_LATEST]['attributes']['params']['pointer'] is None

        res = app.get(public_url, auth=contrib.auth)
        assert res.status_code == 200
        assert res.json['data'][API_LATEST]['attributes']['params']['pointer'] is None

    def test_registration_pointers(
            self, app, user, user_auth, non_contrib,
            public_project, pointer_registration, public_url):
        public_project.add_pointer(
            pointer_registration, auth=user_auth, save=True)
        assert public_project.logs.latest().action == 'pointer_created'
        res = app.get(public_url, auth=user.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == public_project.logs.count()
        assert res.json['data'][API_LATEST]['attributes']['action'] == 'pointer_created'
        assert res.json['data'][API_LATEST]['relationships']['linked_registration']['data']['id'] == pointer_registration._id

        # Confirm pointer contains correct data for various users
        assert res.json['data'][API_LATEST]['attributes']['params']['pointer']['id'] == pointer_registration._id

        res = app.get(public_url, auth=non_contrib.auth)
        assert res.status_code == 200
        assert res.json['data'][API_LATEST]['attributes']['params']['pointer']['id'] == pointer_registration._id

        res = app.get(public_url)
        assert res.status_code == 200
        assert res.json['data'][API_LATEST]['attributes']['params']['pointer']['id'] == pointer_registration._id

        # Delete pointer and make sure no data shown
        pointer_registration.remove_node(Auth(user))

        res = app.get(public_url, auth=user.auth)
        assert res.status_code == 200
        assert res.json['data'][API_LATEST]['attributes']['params']['pointer'] is None

        res = app.get(public_url)
        assert res.status_code == 200
        assert res.json['data'][API_LATEST]['attributes']['params']['pointer'] is None

        res = app.get(public_url, auth=non_contrib.auth)
        assert res.status_code == 200
        assert res.json['data'][API_LATEST]['attributes']['params']['pointer'] is None

    def test_embargo_pointers(
            self, app, user, user_auth, non_contrib,
            public_project, pointer_embargo, public_url):
        public_project.add_pointer(pointer_embargo, auth=user_auth, save=True)
        assert public_project.logs.latest().action == 'pointer_created'
        res = app.get(public_url, auth=user.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == public_project.logs.count()
        assert res.json['data'][API_LATEST]['attributes']['action'] == 'pointer_created'
        assert res.json['data'][API_LATEST]['relationships']['linked_registration']['data']['id'] == pointer_embargo._id

        # Confirm pointer contains correct data for various users
        assert res.json['data'][API_LATEST]['attributes']['params']['pointer']['id'] == pointer_embargo._id

        res = app.get(public_url, auth=non_contrib.auth)
        assert res.status_code == 200
        assert res.json['data'][API_LATEST]['attributes']['params']['pointer'] is None

        res = app.get(public_url)
        assert res.status_code == 200
        assert res.json['data'][API_LATEST]['attributes']['params']['pointer'] is None

        # Delete pointer and make sure no data shown
        pointer_embargo.remove_node(Auth(user))

        res = app.get(public_url, auth=user.auth)
        assert res.status_code == 200
        assert res.json['data'][API_LATEST]['attributes']['params']['pointer'] is None

        res = app.get(public_url)
        assert res.status_code == 200
        assert res.json['data'][API_LATEST]['attributes']['params']['pointer'] is None

        res = app.get(public_url, auth=non_contrib.auth)
        assert res.status_code == 200
        assert res.json['data'][API_LATEST]['attributes']['params']['pointer'] is None


@pytest.mark.django_db
class TestNodeLogFiltering(TestNodeLogList):

    def test_filter_action_not_equal(
            self, app, user, user_auth, public_project):
        public_project.add_tag('Rheisen', auth=user_auth)
        assert public_project.logs.latest().action == 'tag_added'
        url = '/{}nodes/{}/logs/?filter[action][ne]=tag_added'.format(
            API_BASE, public_project._id)
        res = app.get(url, auth=user.auth)
        assert len(res.json['data']) == 1
        assert res.json['data'][API_LATEST]['attributes']['action'] == 'project_created'

    def test_filter_date_not_equal(self, app, user, public_project, pointer):
        public_project.add_pointer(pointer, auth=Auth(user), save=True)
        assert public_project.logs.latest().action == 'pointer_created'
        assert public_project.logs.count() == 2

        pointer_added_log = public_project.logs.get(action='pointer_created')
        date_pointer_added = str(pointer_added_log.date).split(
            '+')[0].replace(' ', 'T')

        url = '/{}nodes/{}/logs/?filter[date][ne]={}'.format(
            API_BASE, public_project._id, date_pointer_added)
        res = app.get(url, auth=user.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == 1
        assert res.json['data'][API_LATEST]['attributes']['action'] == 'project_created'

    def test_filter_end_date(self, app, user, public_project, pointer):
        public_project.add_pointer(pointer, auth=Auth(user), save=True)
        assert public_project.logs.latest().action == 'pointer_created'
        assert public_project.logs.count() == 2

        pointer_added_log = public_project.logs.get(action='pointer_created')
        date_pointer_added = pointer_added_log.date.strftime('%Y-%m-%dT%H:%M')

        url = '/{}nodes/{}/logs/?filter[date][lte]={}'.format(
            API_BASE, public_project._id, date_pointer_added)
        res = app.get(url, auth=user.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == 2
        assert res.json['data'][API_LATEST]['attributes']['action'] == 'pointer_created'

    def test_filter_end_date_unsupported_format(self, app, user, public_project, pointer):
        # make sure project created and pointer created logs are not in the same second
        time.sleep(1)
        public_project.add_pointer(pointer, auth=Auth(user), save=True)
        assert public_project.logs.latest().action == 'pointer_created'
        assert public_project.logs.count() == 2

        pointer_added_log = public_project.logs.get(action='pointer_created')
        date_pointer_added = pointer_added_log.date.strftime('%Y-%m-%d %H:%M:%S')

        url = '/{}nodes/{}/logs/?filter[date][lte]={}'.format(
            API_BASE, public_project._id, date_pointer_added)
        res = app.get(url, auth=user.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == 1
        assert res.json['data'][API_LATEST]['attributes']['action'] == 'project_created'


@pytest.mark.django_db
class TestLogStorageName(ApiTestCase):

    def setUp(self):
        super(TestLogStorageName, self).setUp()
        self.user = AuthUserFactory()
        self.node = ProjectFactory(creator=self.user)

    def add_folder_created_log(self):
        self.node.add_log(
            'osf_storage_folder_created',
            auth=Auth(self.user),
            params={
                'node': self.node._id,
                'path': 'test_folder',
                'urls': {'url1': 'www.fake.org', 'url2': 'www.fake.com'},
                'source': {
                    'materialized': 'test_folder',
                    'addon': 'osfstorage',
                    'node': {
                        '_id': self.node._id,
                        'url': 'index.html',
                        'title': 'Hello World',
                    }
                }
            },
        )

    def test_unrelated_to_storage(self):
        url = '/{}nodes/{}/logs/'.format(API_BASE, self.node._id)
        res = self.app.get(url, auth=self.user.auth)

        log = res.json['data'][0]['attributes']
        assert log['action'] == 'project_created'
        assert log['params']['storage_name'] is None

    def test_no_storage_type(self):
        ProjectStorageType.objects.filter(node=self.node).delete()

        self.add_folder_created_log()
        url = '/{}nodes/{}/logs/'.format(API_BASE, self.node._id)
        res = self.app.get(url, auth=self.user.auth)

        log = res.json['data'][0]['attributes']
        assert log['action'] == 'osf_storage_folder_created'
        assert log['params']['storage_name'] == 'NII Storage'

    def test_nii_storage(self):
        self.add_folder_created_log()
        url = '/{}nodes/{}/logs/'.format(API_BASE, self.node._id)
        res = self.app.get(url, auth=self.user.auth)

        log = res.json['data'][0]['attributes']
        assert log['action'] == 'osf_storage_folder_created'
        assert log['params']['storage_name'] == 'NII Storage'

    @mock.patch('api.logs.serializers.logging')
    def test_custom_storage_no_institution(self, mock_logging):
        ProjectStorageType.objects.filter(node=self.node).update(
            storage_type=ProjectStorageType.CUSTOM_STORAGE
        )

        self.add_folder_created_log()
        url = '/{}nodes/{}/logs/'.format(API_BASE, self.node._id)
        res = self.app.get(url, auth=self.user.auth)

        log = res.json['data'][0]['attributes']
        assert log['action'] == 'osf_storage_folder_created'
        assert log['params']['storage_name'] == 'Institutional Storage'

        assert mock_logging.warning.call_count == 1
        mock_logging.warning.assert_called_with('Unable to retrieve storage name: Institution not found')

    @mock.patch('api.logs.serializers.logging')
    def test_custom_storage_no_region(self, mock_logging):
        ProjectStorageType.objects.filter(node=self.node).update(
            storage_type=ProjectStorageType.CUSTOM_STORAGE
        )
        institution = InstitutionFactory()
        self.user.affiliated_institutions.add(institution)

        self.add_folder_created_log()
        url = '/{}nodes/{}/logs/'.format(API_BASE, self.node._id)
        res = self.app.get(url, auth=self.user.auth)

        log = res.json['data'][0]['attributes']
        assert log['action'] == 'osf_storage_folder_created'
        assert log['params']['storage_name'] == 'Institutional Storage'

        assert mock_logging.warning.call_count == 1
        mock_logging.warning.assert_called_with('Unable to retrieve storage name from institution ID {}'.format(institution.id))

    def test_custom_storage_get_name(self):
        ProjectStorageType.objects.filter(node=self.node).update(
            storage_type=ProjectStorageType.CUSTOM_STORAGE
        )
        institution = InstitutionFactory()
        self.user.affiliated_institutions.add(institution)
        RegionFactory(_id=institution._id, name='Kitten Storage')

        self.add_folder_created_log()
        url = '/{}nodes/{}/logs/'.format(API_BASE, self.node._id)
        res = self.app.get(url, auth=self.user.auth)

        log = res.json['data'][0]['attributes']
        assert log['action'] == 'osf_storage_folder_created'
        assert log['params']['storage_name'] == 'Kitten Storage'


@pytest.mark.django_db
class TestNodeLogDownload(TestNodeLogList):
    @pytest.fixture()
    def download_url(self, public_project):
        return '/{}nodes/{}/logs/?action=download'.format(
            API_BASE, public_project._id)

    def test_download__include_embed_user_query_param(self, app, user, public_project):
        QuickFilesNode.objects.get_or_create(
            title='title',
            creator=user
        )
        public_url = '/{}nodes/{}/logs/?embed=user&action=download'.format(
            API_BASE, public_project._id)
        res = app.get(public_url, auth=user.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == public_project.logs.count()
        assert_datetime_equal(
            parse_date(
                res.json['data'][API_LATEST]['date']),
            public_project.logs.first().date)
        assert res.json['data'][API_LATEST]['user'] == user.fullname
        assert res.json['data'][API_LATEST]['project_id'] == public_project._id
        assert res.json['data'][API_LATEST]['project_title'] == public_project.title
        assert res.json['data'][API_LATEST]['action'] == public_project.logs.first().action

    def test_download__limited_by_page_size(self, app, user, user_auth, private_project):
        private_project.add_tag('tag', auth=user_auth)
        download_url = '/{}nodes/{}/logs/?page[size]=1&action=download'.format(
            API_BASE, private_project._id)
        res = app.get(download_url, auth=user.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == 1
        assert_datetime_equal(
            parse_date(
                res.json['data'][API_LATEST]['date']),
            private_project.logs.first().date)
        assert res.json['data'][API_LATEST]['project_id'] == private_project._id
        assert res.json['data'][API_LATEST]['project_title'] == private_project.title
        assert res.json['data'][API_LATEST]['action'] == private_project.logs.last().action

    def test_download__params_include_contributors(self, app, user, contrib, user_auth, public_project, download_url):
        # Add contributor
        public_project.add_contributor(contrib, auth=user_auth)
        assert public_project.logs.latest().action == 'contributor_added'
        # Remove contributor
        with disconnected_from_listeners(contributor_removed):
            public_project.remove_contributor(contrib, auth=user_auth)
        assert public_project.logs.latest().action == 'contributor_removed'
        res = app.get(download_url, auth=user.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == public_project.logs.count()
        # Assert the latest log
        assert res.json['data'][API_LATEST]['action'] == 'contributor_removed'
        assert res.json['data'][API_LATEST]['targetUserFullId'] == contrib._id
        assert res.json['data'][API_LATEST]['targetUserFullName'] == contrib.fullname
        # Assert the second log
        assert res.json['data'][1]['action'] == 'contributor_added'
        assert res.json['data'][1]['targetUserFullId'] == contrib._id
        assert res.json['data'][1]['targetUserFullName'] == contrib.fullname

    def test_download__action_include_checked(self, app, user, user_auth, public_project, download_url):
        public_project.add_log(
            'checked_out',
            auth=Auth(user),
            params={
                'kind': 'file',
                'node': public_project._id,
                'path': 'test_file',
                'urls': {
                    'view': 'www.fake.org',
                    'download': 'www.fake.com',
                },
                'project': public_project._id
            }
        )
        res = app.get(download_url, auth=user.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == public_project.logs.count()
        assert res.json['data'][API_LATEST]['action'] == 'checked_out'
        assert res.json['data'][API_LATEST]['item'] == 'file'
        assert res.json['data'][API_LATEST]['path'] == 'test_file'

    def test_download__action_include_osf_storage(self, app, user, user_auth, public_project, download_url):
        public_project.add_log(
            'osf_storage_folder_created',
            auth=Auth(user),
            params={
                'node': public_project._id,
                'path': 'test_folder',
                'urls': {'url1': 'www.fake.org', 'url2': 'www.fake.com'},
                'source': {
                    'materialized': 'test_folder',
                    'addon': 'osfstorage',
                    'node': {
                        '_id': public_project._id,
                        'url': 'index.html',
                        'title': 'Hello World',
                    }
                }
            },
        )
        res = app.get(download_url, auth=user.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == public_project.logs.count()
        assert res.json['data'][API_LATEST]['action'] == 'osf_storage_folder_created'
        assert res.json['data'][API_LATEST]['path'] == 'test_folder'

    def test_download__action_include_addon(self, app, user, user_auth, public_project, download_url):
        # Add GitHub addon
        public_project.add_addon('github', auth=user_auth)
        assert public_project.logs.latest().action == 'addon_added'
        # Remove GitHub addon
        old_log_length = len(list(public_project.logs.all()))
        public_project.delete_addon('github', auth=user_auth)
        assert public_project.logs.latest().action == 'addon_removed'
        assert (public_project.logs.count() - 1) == old_log_length
        res = app.get(download_url, auth=user.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == public_project.logs.count()
        # Assert the latest log
        assert res.json['data'][API_LATEST]['action'] == 'addon_removed'
        assert res.json['data'][API_LATEST]['addon'] == 'GitHub'
        # Assert the second log
        assert res.json['data'][1]['action'] == 'addon_added'
        assert res.json['data'][1]['addon'] == 'GitHub'

    def test_download__action_include_tag(self, app, user, user_auth, public_project, download_url):
        # Add tag
        public_project.add_tag('Rheisen', auth=user_auth)
        assert public_project.logs.latest().action == 'tag_added'
        # Remove tag
        public_project.remove_tag('Rheisen', auth=user_auth)
        assert public_project.logs.latest().action == 'tag_removed'
        res = app.get(download_url, auth=user)
        assert res.status_code == 200
        assert len(res.json['data']) == public_project.logs.count()
        # Assert the latest log
        assert res.json['data'][API_LATEST]['action'] == 'tag_removed'
        assert res.json['data'][API_LATEST]['tag'] == 'Rheisen'
        # Assert the second log
        assert res.json['data'][1]['action'] == 'tag_added'
        assert res.json['data'][1]['tag'] == 'Rheisen'

    def test_download__action_include_wiki(self, app, user, user_auth, public_project, download_url):
        public_project.add_log(
            'wiki_updated',
            auth=Auth(user),
            params={
                'project': public_project.parent_id,
                'node': public_project._primary_key,
                'page': 'foo',
                'page_id': 'test_guid',
                'version': 1,
            }
        )
        res = app.get(download_url, auth=user.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == public_project.logs.count()
        assert res.json['data'][API_LATEST]['action'] == 'wiki_updated'
        assert res.json['data'][API_LATEST]['version'] == '1'
        assert res.json['data'][API_LATEST]['page'] == 'foo'
