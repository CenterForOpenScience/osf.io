import datetime
import pytest
import pytz
import urlparse

from dateutil.parser import parse as parse_date

from api.base.settings.defaults import API_BASE
from framework.auth.core import Auth
from osf.models import NodeLog, Registration, Sanction
from osf_tests.factories import (
    AuthUserFactory,
    ProjectFactory,
    RegistrationFactory,
    EmbargoFactory,
)
from tests.base import assert_datetime_equal
from website.util import disconnected_from_listeners
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
        return RegistrationFactory(creator=user, embargo=EmbargoFactory(user=user), is_public=False)

    @pytest.fixture()
    def private_project(self, user):
        return ProjectFactory(is_public=False, creator=user)

    @pytest.fixture()
    def private_url(self, private_project):
        return '/{}nodes/{}/logs/?version=2.2'.format(API_BASE, private_project._id)

    @pytest.fixture()
    def public_project(self, user):
        return ProjectFactory(is_public=True, creator=user)

    @pytest.fixture()
    def public_url(self, public_project):
        return '/{}nodes/{}/logs/?version=2.2'.format(API_BASE, public_project._id)

    def test_add_tag(self, app, user, user_auth, public_project, public_url):
        public_project.add_tag('Rheisen', auth=user_auth)
        assert public_project.logs.latest().action == 'tag_added'
        res = app.get(public_url, auth=user.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == public_project.logs.count()
        assert res.json['data'][API_LATEST]['attributes']['action'] == 'tag_added'
        assert 'Rheisen' == public_project.logs.latest().params['tag']

    def test_remove_tag(self, app, user, user_auth, public_project, public_url):
        public_project.add_tag('Rheisen', auth=user_auth)
        assert public_project.logs.latest().action == 'tag_added'
        public_project.remove_tag('Rheisen', auth=user_auth)
        assert public_project.logs.latest().action == 'tag_removed'
        res = app.get(public_url, auth=user)
        assert res.status_code == 200
        assert len(res.json['data']) == public_project.logs.count()
        assert res.json['data'][API_LATEST]['attributes']['action'] == 'tag_removed'
        assert public_project.logs.latest().params['tag'] == 'Rheisen'

    def test_project_creation(self, app, user, public_project, private_project, public_url, private_url):

    #   test_project_created
        res = app.get(public_url)
        assert res.status_code == 200
        assert len(res.json['data']) == public_project.logs.count()
        assert public_project.logs.first().action == 'project_created'
        assert public_project.logs.first().action == res.json['data'][API_LATEST]['attributes']['action']

    #   test_log_create_on_public_project
        res = app.get(public_url)
        assert res.status_code == 200
        assert len(res.json['data']) == public_project.logs.count()
        assert_datetime_equal(parse_date(res.json['data'][API_FIRST]['attributes']['date']),
                              public_project.logs.first().date)
        assert res.json['data'][API_FIRST]['attributes']['action'] == public_project.logs.first().action

    #   test_log_create_on_private_project
        res = app.get(private_url, auth=user.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == public_project.logs.count()
        assert_datetime_equal(parse_date(res.json['data'][API_FIRST]['attributes']['date']),
                              private_project.logs.first().date)
        assert res.json['data'][API_FIRST]['attributes']['action'] == private_project.logs.first().action

    def test_add_addon(self, app, user, user_auth, public_project, public_url):
        public_project.add_addon('github', auth=user_auth)
        assert public_project.logs.latest().action == 'addon_added'
        res = app.get(public_url, auth=user.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == public_project.logs.count()
        assert res.json['data'][API_LATEST]['attributes']['action'] == 'addon_added'

    def test_project_add_remove_contributor(self, app, user, contrib, user_auth, public_project, public_url):
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

    def test_remove_addon(self, app, user, user_auth, public_project, public_url):
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

    def test_pointers(self, app, user, user_auth, contrib, public_project, pointer, public_url):
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
        pointer.save()

        res = app.get(public_url, auth=user.auth)
        assert res.status_code == 200
        assert res.json['data'][API_LATEST]['attributes']['params']['pointer'] is None
        
        res = app.get(public_url)
        assert res.status_code == 200
        assert res.json['data'][API_LATEST]['attributes']['params']['pointer'] is None

        res = app.get(public_url, auth=contrib.auth)
        assert res.status_code == 200
        assert res.json['data'][API_LATEST]['attributes']['params']['pointer'] is None

    def test_registration_pointers(self, app, user, user_auth, non_contrib, public_project, pointer_registration, public_url):
        public_project.add_pointer(pointer_registration, auth=user_auth, save=True)
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
        pointer_registration.save()

        res = app.get(public_url, auth=user.auth)
        assert res.status_code == 200
        assert res.json['data'][API_LATEST]['attributes']['params']['pointer'] is None
        
        res = app.get(public_url)
        assert res.status_code == 200
        assert res.json['data'][API_LATEST]['attributes']['params']['pointer'] is None

        res = app.get(public_url, auth=non_contrib.auth)
        assert res.status_code == 200
        assert res.json['data'][API_LATEST]['attributes']['params']['pointer'] is None

    def test_embargo_pointers(self, app, user, user_auth, non_contrib, public_project, pointer_embargo, public_url):
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
        pointer_embargo.save()

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

    def test_filter_action_not_equal(self, app, user, user_auth, public_project):
        public_project.add_tag('Rheisen', auth=user_auth)
        assert public_project.logs.latest().action == 'tag_added'
        url = '/{}nodes/{}/logs/?filter[action][ne]=tag_added'.format(API_BASE, public_project._id)
        res = app.get(url, auth=user.auth)
        assert len(res.json['data']) == 1
        assert res.json['data'][API_LATEST]['attributes']['action'] == 'project_created'

    def test_filter_date_not_equal(self, app, user, public_project, pointer):
        public_project.add_pointer(pointer, auth=Auth(user), save=True)
        assert public_project.logs.latest().action == 'pointer_created'
        assert public_project.logs.count() == 2

        pointer_added_log = public_project.logs.get(action='pointer_created')
        date_pointer_added = str(pointer_added_log.date).split('+')[0].replace(' ', 'T')

        url = '/{}nodes/{}/logs/?filter[date][ne]={}'.format(API_BASE, public_project._id, date_pointer_added)
        res = app.get(url, auth=user.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == 1
        assert res.json['data'][API_LATEST]['attributes']['action'] == 'project_created'
