"""Views tests for the OSF."""
from urllib import parse

import unittest
from unittest import mock
from urllib.parse import quote_plus

import pytest
from django.core.exceptions import ValidationError
from django.utils import timezone
from rest_framework import status as http_status

from addons.osfstorage import settings as osfstorage_settings
from addons.wiki.models import WikiPage
from framework import auth
from framework.auth import Auth
from framework.auth.utils import ensure_external_identity_uniqueness
from framework.exceptions import HTTPError, TemplateHTTPError
from framework.transactions.handlers import no_auto_transaction
from osf.models import (
    Comment,
    OSFUser,
    SpamStatus,
    NodeRelation,
)
from osf.utils import permissions
from osf_tests.factories import (
    fake_email,
    AuthUserFactory,
    CommentFactory,
    NodeFactory,
    OSFGroupFactory,
    PreprintFactory,
    PreprintProviderFactory,
    PrivateLinkFactory,
    ProjectFactory,
    UserFactory,
    UnconfirmedUserFactory,
)
from tests.base import (
    assert_is_redirect,
    capture_signals,
    fake,
    OsfTestCase,
    assert_datetime_equal,
    test_app
)
from website.project.decorators import check_can_access
from website.project.model import has_anonymous_link
from website.project.views.node import _should_show_wiki_widget
from website.util import web_url_for
from website.util import rubeus

pytestmark = pytest.mark.django_db


@test_app.route('/errorexc')
def error_exc():
    UserFactory()
    raise RuntimeError

@test_app.route('/error500')
def error500():
    UserFactory()
    return 'error', 500

@test_app.route('/noautotransact')
@no_auto_transaction
def no_auto_transact():
    UserFactory()
    return 'error', 500

class TestViewsAreAtomic(OsfTestCase):
    def test_error_response_rolls_back_transaction(self):
        original_user_count = OSFUser.objects.count()
        self.app.get('/error500')
        assert OSFUser.objects.count() == original_user_count

        # Need to set debug = False in order to rollback transactions in transaction_teardown_request
        test_app.debug = False
        try:
            self.app.get('/errorexc')
        except RuntimeError:
            pass
        test_app.debug = True

        self.app.get('/noautotransact')
        assert OSFUser.objects.count() == original_user_count + 1


@pytest.mark.enable_bookmark_creation
class TestViewingProjectWithPrivateLink(OsfTestCase):

    def setUp(self):
        super().setUp()
        self.user = AuthUserFactory()  # Is NOT a contributor
        self.project = ProjectFactory(is_public=False)
        self.link = PrivateLinkFactory()
        self.link.nodes.add(self.project)
        self.link.save()
        self.project_url = self.project.web_url_for('view_project')

    def test_edit_private_link_empty(self):
        node = ProjectFactory(creator=self.user)
        link = PrivateLinkFactory()
        link.nodes.add(node)
        link.save()
        url = node.api_url_for('project_private_link_edit')
        res = self.app.put(url, json={'pk': link._id, 'value': ''}, auth=self.user.auth)
        assert res.status_code == 400
        assert 'Title cannot be blank' in res.text

    def test_edit_private_link_invalid(self):
        node = ProjectFactory(creator=self.user)
        link = PrivateLinkFactory()
        link.nodes.add(node)
        link.save()
        url = node.api_url_for('project_private_link_edit')
        res = self.app.put(url, json={'pk': link._id, 'value': '<a></a>'}, auth=self.user.auth)
        assert res.status_code == 400
        assert 'Invalid link name.' in res.text

    @mock.patch('framework.auth.core.Auth.private_link')
    def test_can_be_anonymous_for_public_project(self, mock_property):
        mock_property.return_value(mock.MagicMock())
        mock_property.anonymous = True
        anonymous_link = PrivateLinkFactory(anonymous=True)
        anonymous_link.nodes.add(self.project)
        anonymous_link.save()
        self.project.set_privacy('public')
        self.project.save()
        self.project.reload()
        auth = Auth(user=self.user, private_key=anonymous_link.key)
        assert has_anonymous_link(self.project, auth)

    def test_has_private_link_key(self):
        res = self.app.get(self.project_url, query_string={'view_only': self.link.key})
        assert res.status_code == 200

    def test_not_logged_in_no_key(self):
        res = self.app.get(self.project_url, query_string={'view_only': None})
        assert_is_redirect(res)
        res = self.app.resolve_redirect(res)
        assert res.status_code == 308
        assert res.request.path == '/login'

    def test_logged_in_no_private_key(self):
        res = self.app.get(self.project_url, query_string={'view_only': None}, auth=self.user.auth)
        assert res.status_code == http_status.HTTP_403_FORBIDDEN

    def test_logged_in_has_key(self):
        res = self.app.get(self.project_url, query_string={'view_only': self.link.key}, auth=self.user.auth)
        assert res.status_code == 200

    @unittest.skip('Skipping for now until we find a way to mock/set the referrer')
    def test_prepare_private_key(self):
        res = self.app.get(self.project_url, query_string={'key': self.link.key})

        res = res.click('Registrations')

        assert_is_redirect(res)
        res = self.app.get(self.project_url, query_string={'key': self.link.key}, follow_redirects=True)

        assert res.status_code == 200
        assert res.request.GET['key'] == self.link.key

    def test_cannot_access_registrations_or_forks_with_anon_key(self):
        anonymous_link = PrivateLinkFactory(anonymous=True)
        anonymous_link.nodes.add(self.project)
        anonymous_link.save()
        self.project.is_public = False
        self.project.save()
        url = self.project_url + f'registrations/?view_only={anonymous_link.key}'
        res = self.app.get(url)

        assert res.status_code == 401

    def test_can_access_registrations_and_forks_with_not_anon_key(self):
        link = PrivateLinkFactory(anonymous=False)
        link.nodes.add(self.project)
        link.save()
        self.project.is_public = False
        self.project.save()
        url = self.project_url + f'registrations/?view_only={self.link.key}'
        res = self.app.get(url)

        assert res.status_code == 302
        assert url.replace('/project/', '') in res.location

    def test_check_can_access_valid(self):
        contributor = AuthUserFactory()
        self.project.add_contributor(contributor, auth=Auth(self.project.creator))
        self.project.save()
        assert check_can_access(self.project, contributor)

    def test_check_can_access_osf_group_member_valid(self):
        user = AuthUserFactory()
        group = OSFGroupFactory(creator=user)
        self.project.add_osf_group(group, permissions.READ)
        self.project.save()
        assert check_can_access(self.project, user)

    def test_check_user_access_invalid(self):
        noncontrib = AuthUserFactory()
        with pytest.raises(HTTPError):
            check_can_access(self.project, noncontrib)

    def test_check_user_access_if_user_is_None(self):
        assert not check_can_access(self.project, None)

    def test_check_can_access_invalid_access_requests_enabled(self):
        noncontrib = AuthUserFactory()
        assert self.project.access_requests_enabled
        with pytest.raises(TemplateHTTPError):
            check_can_access(self.project, noncontrib)

    def test_check_can_access_invalid_access_requests_disabled(self):
        noncontrib = AuthUserFactory()
        self.project.access_requests_enabled = False
        self.project.save()
        with pytest.raises(HTTPError):
            check_can_access(self.project, noncontrib)

    def test_logged_out_user_cannot_view_spammy_project_via_private_link(self):
        self.project.spam_status = SpamStatus.SPAM
        self.project.save()
        res = self.app.get(self.project_url, query_string={'view_only': self.link.key})
        # Logged out user gets redirected to login page
        assert res.status_code == 302

    def test_logged_in_user_cannot_view_spammy_project_via_private_link(self):
        rando_user = AuthUserFactory()
        self.project.spam_status = SpamStatus.SPAM
        self.project.save()
        res = self.app.get(
            self.project_url,
            query_string={'view_only': self.link.key},
            auth=rando_user.auth,
        )
        assert res.status_code == 403


class TestEditableChildrenViews(OsfTestCase):

    def setUp(self):
        OsfTestCase.setUp(self)
        self.user = AuthUserFactory()
        self.project = ProjectFactory(creator=self.user, is_public=False)
        self.child = ProjectFactory(parent=self.project, creator=self.user, is_public=True)
        self.grandchild = ProjectFactory(parent=self.child, creator=self.user, is_public=False)
        self.great_grandchild = ProjectFactory(parent=self.grandchild, creator=self.user, is_public=True)
        self.great_great_grandchild = ProjectFactory(parent=self.great_grandchild, creator=self.user, is_public=False)
        url = self.project.api_url_for('get_editable_children')
        self.project_results = self.app.get(url, auth=self.user.auth).json

    def test_get_editable_children(self):
        assert len(self.project_results['children']) == 4
        assert self.project_results['node']['id'] == self.project._id

    def test_editable_children_order(self):
        assert self.project_results['children'][0]['id'] == self.child._id
        assert self.project_results['children'][1]['id'] == self.grandchild._id
        assert self.project_results['children'][2]['id'] == self.great_grandchild._id
        assert self.project_results['children'][3]['id'] == self.great_great_grandchild._id

    def test_editable_children_indents(self):
        assert self.project_results['children'][0]['indent'] == 0
        assert self.project_results['children'][1]['indent'] == 1
        assert self.project_results['children'][2]['indent'] == 2
        assert self.project_results['children'][3]['indent'] == 3

    def test_editable_children_parents(self):
        assert self.project_results['children'][0]['parent_id'] == self.project._id
        assert self.project_results['children'][1]['parent_id'] == self.child._id
        assert self.project_results['children'][2]['parent_id'] == self.grandchild._id
        assert self.project_results['children'][3]['parent_id'] == self.great_grandchild._id

    def test_editable_children_privacy(self):
        assert not self.project_results['node']['is_public']
        assert self.project_results['children'][0]['is_public']
        assert not self.project_results['children'][1]['is_public']
        assert self.project_results['children'][2]['is_public']
        assert not self.project_results['children'][3]['is_public']

    def test_editable_children_titles(self):
        assert self.project_results['node']['title'] == self.project.title
        assert self.project_results['children'][0]['title'] == self.child.title
        assert self.project_results['children'][1]['title'] == self.grandchild.title
        assert self.project_results['children'][2]['title'] == self.great_grandchild.title
        assert self.project_results['children'][3]['title'] == self.great_great_grandchild.title


class TestGetNodeTree(OsfTestCase):

    def setUp(self):
        OsfTestCase.setUp(self)
        self.user = AuthUserFactory()
        self.user2 = AuthUserFactory()

    def test_get_single_node(self):
        project = ProjectFactory(creator=self.user)
        # child = NodeFactory(parent=project, creator=self.user)

        url = project.api_url_for('get_node_tree')
        res = self.app.get(url, auth=self.user.auth)

        node_id = res.json[0]['node']['id']
        assert node_id == project._primary_key

    def test_get_node_with_children(self):
        project = ProjectFactory(creator=self.user)
        child1 = NodeFactory(parent=project, creator=self.user)
        child2 = NodeFactory(parent=project, creator=self.user2)
        child3 = NodeFactory(parent=project, creator=self.user)
        url = project.api_url_for('get_node_tree')
        res = self.app.get(url, auth=self.user.auth)
        tree = res.json[0]
        parent_node_id = tree['node']['id']
        child_ids = [child['node']['id'] for child in tree['children']]

        assert parent_node_id == project._primary_key
        assert child1._primary_key in child_ids
        assert child2._primary_key in child_ids
        assert child3._primary_key in child_ids

    def test_get_node_with_child_linked_to_parent(self):
        project = ProjectFactory(creator=self.user)
        child1 = NodeFactory(parent=project, creator=self.user)
        child1.save()
        url = project.api_url_for('get_node_tree')
        res = self.app.get(url, auth=self.user.auth)
        tree = res.json[0]
        parent_node_id = tree['node']['id']
        child1_id = tree['children'][0]['node']['id']
        assert child1_id == child1._primary_key

    def test_get_node_not_parent_owner(self):
        project = ProjectFactory(creator=self.user2)
        child = NodeFactory(parent=project, creator=self.user2)
        url = project.api_url_for('get_node_tree')
        res = self.app.get(url, auth=self.user.auth)
        assert res.status_code == 200
        assert res.json == []

    # Parent node should show because of user2 read access, and only child3
    def test_get_node_parent_not_admin(self):
        project = ProjectFactory(creator=self.user)
        project.add_contributor(self.user2, auth=Auth(self.user))
        project.save()
        child1 = NodeFactory(parent=project, creator=self.user)
        child2 = NodeFactory(parent=project, creator=self.user)
        child3 = NodeFactory(parent=project, creator=self.user)
        child3.add_contributor(self.user2, auth=Auth(self.user))
        url = project.api_url_for('get_node_tree')
        res = self.app.get(url, auth=self.user2.auth)
        tree = res.json[0]
        parent_node_id = tree['node']['id']
        children = tree['children']
        assert parent_node_id == project._primary_key
        assert len(children) == 1
        assert children[0]['node']['id'] == child3._primary_key


class TestPublicViews(OsfTestCase):

    def test_explore(self):
        res = self.app.get('/explore/', follow_redirects=True)
        assert res.status_code == 200


class TestExternalAuthViews(OsfTestCase):

    def setUp(self):
        super().setUp()
        name, email = fake.name(), fake_email()
        self.provider_id = fake.ean()
        external_identity = {
            'orcid': {
                self.provider_id: 'CREATE'
            }
        }
        password = str(fake.password())
        self.user = OSFUser.create_unconfirmed(
            username=email,
            password=password,
            fullname=name,
            external_identity=external_identity,
        )
        self.user.save()
        self.auth = (self.user.username, password)

    def test_external_login_email_get_with_invalid_session(self):
        url = web_url_for('external_login_email_get')
        resp = self.app.get(url)
        assert resp.status_code == 401

    def test_external_login_confirm_email_get_with_another_user_logged_in(self):
        # TODO: check in qa url encoding
        another_user = AuthUserFactory()
        url = self.user.get_confirmation_url(self.user.username, external_id_provider='orcid', destination='dashboard')
        res = self.app.get(url, auth=another_user.auth)
        assert res.status_code == 302, 'redirects to cas logout'
        assert '/logout?service=' in res.location
        assert quote_plus(url) in res.location

    def test_external_login_confirm_email_get_without_destination(self):
        url = self.user.get_confirmation_url(self.user.username, external_id_provider='orcid')
        res = self.app.get(url, auth=self.auth)
        assert res.status_code == 400, 'bad request'

    @mock.patch('website.mails.send_mail')
    def test_external_login_confirm_email_get_create(self, mock_welcome):
        # TODO: check in qa url encoding
        assert not self.user.is_registered
        url = self.user.get_confirmation_url(self.user.username, external_id_provider='orcid', destination='dashboard')
        res = self.app.get(url)
        assert res.status_code == 302, 'redirects to cas login'
        assert '/login?service=' in res.location
        assert quote_plus('new=true') in res.location

        assert mock_welcome.call_count == 0

        self.user.reload()
        assert self.user.external_identity['orcid'][self.provider_id] == 'VERIFIED'
        assert self.user.is_registered
        assert self.user.has_usable_password()

    @mock.patch('website.mails.send_mail')
    def test_external_login_confirm_email_get_link(self, mock_link_confirm):
        self.user.external_identity['orcid'][self.provider_id] = 'LINK'
        self.user.save()
        assert not self.user.is_registered
        url = self.user.get_confirmation_url(self.user.username, external_id_provider='orcid', destination='dashboard')
        res = self.app.get(url)
        assert res.status_code == 302, 'redirects to cas login'
        assert 'You should be redirected automatically' in str(res.html)
        assert '/login?service=' in res.location
        assert 'new=true' not in parse.unquote(res.location)

        assert mock_link_confirm.call_count == 1

        self.user.reload()
        assert self.user.external_identity['orcid'][self.provider_id] == 'VERIFIED'
        assert self.user.is_registered
        assert self.user.has_usable_password()

    @mock.patch('website.mails.send_mail')
    def test_external_login_confirm_email_get_duped_id(self, mock_confirm):
        dupe_user = UserFactory(external_identity={'orcid': {self.provider_id: 'CREATE'}})
        assert dupe_user.external_identity == self.user.external_identity
        url = self.user.get_confirmation_url(self.user.username, external_id_provider='orcid', destination='dashboard')
        res = self.app.get(url)
        assert res.status_code == 302, 'redirects to cas login'
        assert 'You should be redirected automatically' in str(res.html)
        assert '/login?service=' in res.location

        assert mock_confirm.call_count == 0

        self.user.reload()
        dupe_user.reload()

        assert self.user.external_identity['orcid'][self.provider_id] == 'VERIFIED'
        assert dupe_user.external_identity == {}

    @mock.patch('website.mails.send_mail')
    def test_external_login_confirm_email_get_duping_id(self, mock_confirm):
        dupe_user = UserFactory(external_identity={'orcid': {self.provider_id: 'VERIFIED'}})
        url = self.user.get_confirmation_url(self.user.username, external_id_provider='orcid', destination='dashboard')
        res = self.app.get(url)
        assert res.status_code == 403, 'only allows one user to link an id'

        assert mock_confirm.call_count == 0

        self.user.reload()
        dupe_user.reload()

        assert dupe_user.external_identity['orcid'][self.provider_id] == 'VERIFIED'
        assert self.user.external_identity == {}

    def test_ensure_external_identity_uniqueness_unverified(self):
        dupe_user = UserFactory(external_identity={'orcid': {self.provider_id: 'CREATE'}})
        assert dupe_user.external_identity == self.user.external_identity

        ensure_external_identity_uniqueness('orcid', self.provider_id, self.user)

        dupe_user.reload()
        self.user.reload()

        assert dupe_user.external_identity == {}
        assert self.user.external_identity == {'orcid': {self.provider_id: 'CREATE'}}

    def test_ensure_external_identity_uniqueness_verified(self):
        dupe_user = UserFactory(external_identity={'orcid': {self.provider_id: 'VERIFIED'}})
        assert dupe_user.external_identity == {'orcid': {self.provider_id: 'VERIFIED'}}
        assert dupe_user.external_identity != self.user.external_identity

        with pytest.raises(ValidationError):
            ensure_external_identity_uniqueness('orcid', self.provider_id, self.user)

        dupe_user.reload()
        self.user.reload()

        assert dupe_user.external_identity == {'orcid': {self.provider_id: 'VERIFIED'}}
        assert self.user.external_identity == {}

    def test_ensure_external_identity_uniqueness_multiple(self):
        dupe_user = UserFactory(external_identity={'orcid': {self.provider_id: 'CREATE'}})
        assert dupe_user.external_identity == self.user.external_identity

        ensure_external_identity_uniqueness('orcid', self.provider_id)

        dupe_user.reload()
        self.user.reload()

        assert dupe_user.external_identity == {}
        assert self.user.external_identity == {}

# TODO: Use mock add-on
class TestAddonUserViews(OsfTestCase):

    def setUp(self):
        super().setUp()
        self.user = AuthUserFactory()

    def test_choose_addons_add(self):
        """Add add-ons; assert that add-ons are attached to project.

        """
        url = '/api/v1/settings/addons/'
        self.app.post(
            url,
            json={'github': True},
            auth=self.user.auth
        , follow_redirects=True)
        self.user.reload()
        assert self.user.get_addon('github')

    def test_choose_addons_remove(self):
        # Add, then delete, add-ons; assert that add-ons are not attached to
        # project.
        url = '/api/v1/settings/addons/'
        self.app.post(
            url,
            json={'github': True},
            auth=self.user.auth
        , follow_redirects=True)
        self.app.post(
            url,
            json={'github': False},
            auth=self.user.auth
        , follow_redirects=True)
        self.user.reload()
        assert not self.user.get_addon('github')


# TODO: Move to OSF Storage
class TestFileViews(OsfTestCase):

    def setUp(self):
        super().setUp()
        self.user = AuthUserFactory()
        self.project = ProjectFactory(creator=self.user, is_public=True)
        self.project.add_contributor(self.user)
        self.project.save()

    def test_grid_data(self):
        url = self.project.api_url_for('grid_data')
        res = self.app.get(url, auth=self.user.auth, follow_redirects=True)
        assert res.status_code == http_status.HTTP_200_OK
        expected = rubeus.to_hgrid(self.project, auth=Auth(self.user))
        data = res.json['data']
        assert len(data) == len(expected)


class TestReorderComponents(OsfTestCase):

    def setUp(self):
        super().setUp()
        self.creator = AuthUserFactory()
        self.contrib = AuthUserFactory()
        # Project is public
        self.project = ProjectFactory.create(creator=self.creator, is_public=True)
        self.project.add_contributor(self.contrib, auth=Auth(self.creator))

        # subcomponent that only creator can see
        self.public_component = NodeFactory(creator=self.creator, is_public=True)
        self.private_component = NodeFactory(creator=self.creator, is_public=False)
        NodeRelation.objects.create(parent=self.project, child=self.public_component)
        NodeRelation.objects.create(parent=self.project, child=self.private_component)

        self.project.save()

    # https://github.com/CenterForOpenScience/openscienceframework.org/issues/489
    def test_reorder_components_with_private_component(self):

        # contrib tries to reorder components
        payload = {
            'new_list': [
                f'{self.private_component._id}',
                f'{self.public_component._id}',
            ]
        }
        url = self.project.api_url_for('project_reorder_components')
        res = self.app.post(url, json=payload, auth=self.contrib.auth)
        assert res.status_code == 200


class TestWikiWidgetViews(OsfTestCase):

    def setUp(self):
        super().setUp()

        # project with no home wiki page
        self.project = ProjectFactory()
        self.read_only_contrib = AuthUserFactory()
        self.project.add_contributor(self.read_only_contrib, permissions=permissions.READ)
        self.noncontributor = AuthUserFactory()

        # project with no home wiki content
        self.project2 = ProjectFactory(creator=self.project.creator)
        self.project2.add_contributor(self.read_only_contrib, permissions=permissions.READ)
        WikiPage.objects.create_for_node(self.project2, 'home', '', Auth(self.project.creator))

    def test_show_wiki_for_contributors_when_no_wiki_or_content(self):
        assert _should_show_wiki_widget(self.project, self.project.creator)
        assert _should_show_wiki_widget(self.project2, self.project.creator)

    def test_show_wiki_is_false_for_read_contributors_when_no_wiki_or_content(self):
        assert not _should_show_wiki_widget(self.project, self.read_only_contrib)
        assert not _should_show_wiki_widget(self.project2, self.read_only_contrib)

    def test_show_wiki_is_false_for_noncontributors_when_no_wiki_or_content(self):
        assert not _should_show_wiki_widget(self.project, None)

    def test_show_wiki_for_osf_group_members(self):
        group = OSFGroupFactory(creator=self.noncontributor)
        self.project.add_osf_group(group, permissions.READ)
        assert not _should_show_wiki_widget(self.project, self.noncontributor)
        assert not _should_show_wiki_widget(self.project2, self.noncontributor)

        self.project.remove_osf_group(group)
        self.project.add_osf_group(group, permissions.WRITE)
        assert _should_show_wiki_widget(self.project, self.noncontributor)
        assert not _should_show_wiki_widget(self.project2, self.noncontributor)


class TestUnconfirmedUserViews(OsfTestCase):

    def test_can_view_profile(self):
        user = UnconfirmedUserFactory()
        url = web_url_for('profile_view_id', uid=user._id)
        res = self.app.get(url)
        assert res.status_code == http_status.HTTP_400_BAD_REQUEST

class TestStaticFileViews(OsfTestCase):

    def test_robots_dot_txt(self):
        res = self.app.get('/robots.txt')
        assert res.status_code == 200
        assert 'User-agent' in res.text
        assert 'html' in res.headers['Content-Type']

    def test_favicon(self):
        res = self.app.get('/favicon.ico')
        assert res.status_code == 200
        assert 'image/vnd.microsoft.icon' in res.headers['Content-Type']

    def test_getting_started_page(self):
        res = self.app.get('/getting-started/')
        assert res.status_code == 302
        assert res.location == 'https://help.osf.io/article/342-getting-started-on-the-osf'
    def test_help_redirect(self):
        res = self.app.get('/help/')
        assert res.status_code == 302


class TestUserConfirmSignal(OsfTestCase):

    def test_confirm_user_signal_called_when_user_claims_account(self):
        unclaimed_user = UnconfirmedUserFactory()
        # unclaimed user has been invited to a project.
        referrer = UserFactory()
        project = ProjectFactory(creator=referrer)
        unclaimed_user.add_unclaimed_record(project, referrer, 'foo', email=fake_email())
        unclaimed_user.save()

        token = unclaimed_user.get_unclaimed_record(project._primary_key)['token']
        with capture_signals() as mock_signals:
            url = web_url_for('claim_user_form', pid=project._id, uid=unclaimed_user._id, token=token)
            payload = {'username': unclaimed_user.username,
                       'password': 'password',
                       'password2': 'password'}
            res = self.app.post(url, data=payload)
            assert res.status_code == 302

        assert mock_signals.signals_sent() == {auth.signals.user_confirmed}

    def test_confirm_user_signal_called_when_user_confirms_email(self):
        unconfirmed_user = UnconfirmedUserFactory()
        unconfirmed_user.save()

        # user goes to email confirmation link
        token = unconfirmed_user.get_confirmation_token(unconfirmed_user.username)
        with capture_signals() as mock_signals:
            url = web_url_for('confirm_email_get', uid=unconfirmed_user._id, token=token)
            res = self.app.get(url)
            assert res.status_code == 302

        assert mock_signals.signals_sent() == {auth.signals.user_confirmed}


# copied from tests/test_comments.py
class TestCommentViews(OsfTestCase):

    def setUp(self):
        super().setUp()
        self.project = ProjectFactory(is_public=True)
        self.user = AuthUserFactory()
        self.project.add_contributor(self.user)
        self.project.save()
        self.user.save()

    def test_view_project_comments_updates_user_comments_view_timestamp(self):
        url = self.project.api_url_for('update_comments_timestamp')
        res = self.app.put(url, json={
            'page': 'node',
            'rootId': self.project._id
        }, auth=self.user.auth)
        self.user.reload()

        user_timestamp = self.user.comments_viewed_timestamp[self.project._id]
        view_timestamp = timezone.now()
        assert_datetime_equal(user_timestamp, view_timestamp)

    def test_confirm_non_contrib_viewers_dont_have_pid_in_comments_view_timestamp(self):
        non_contributor = AuthUserFactory()
        url = self.project.api_url_for('update_comments_timestamp')
        res = self.app.put(url, json={
            'page': 'node',
            'rootId': self.project._id
        }, auth=self.user.auth)

        non_contributor.reload()
        assert self.project._id not in non_contributor.comments_viewed_timestamp

    def test_view_comments_updates_user_comments_view_timestamp_files(self):
        osfstorage = self.project.get_addon('osfstorage')
        root_node = osfstorage.get_root()
        test_file = root_node.append_file('test_file')
        test_file.create_version(self.user, {
            'object': '06d80e',
            'service': 'cloud',
            osfstorage_settings.WATERBUTLER_RESOURCE: 'osf',
        }, {
            'size': 1337,
            'contentType': 'img/png'
        }).save()

        url = self.project.api_url_for('update_comments_timestamp')
        res = self.app.put(url, json={
            'page': 'files',
            'rootId': test_file._id
        }, auth=self.user.auth)
        self.user.reload()

        user_timestamp = self.user.comments_viewed_timestamp[test_file._id]
        view_timestamp = timezone.now()
        assert_datetime_equal(user_timestamp, view_timestamp)

        # Regression test for https://openscience.atlassian.net/browse/OSF-5193
        # moved from tests/test_comments.py
    def test_find_unread_includes_edited_comments(self):
        project = ProjectFactory()
        user = AuthUserFactory()
        project.add_contributor(user, save=True)
        comment = CommentFactory(node=project, user=project.creator)
        n_unread = Comment.find_n_unread(user=user, node=project, page='node')
        assert n_unread == 1

        url = project.api_url_for('update_comments_timestamp')
        payload = {'page': 'node', 'rootId': project._id}
        self.app.put(url, json=payload, auth=user.auth)
        user.reload()
        n_unread = Comment.find_n_unread(user=user, node=project, page='node')
        assert n_unread == 0

        # Edit previously read comment
        comment.edit(
            auth=Auth(project.creator),
            content='edited',
            save=True
        )
        n_unread = Comment.find_n_unread(user=user, node=project, page='node')
        assert n_unread == 1

@mock.patch('website.views.PROXY_EMBER_APPS', False)
class TestResolveGuid(OsfTestCase):
    def setUp(self):
        super().setUp()

    @mock.patch('website.views.use_ember_app')
    def test_preprint_provider_without_domain(self, mock_use_ember_app):
        provider = PreprintProviderFactory(domain='')
        preprint = PreprintFactory(provider=provider)
        url = web_url_for('resolve_guid', _guid=True, guid=preprint._id)
        res = self.app.get(url)
        mock_use_ember_app.assert_called_with()

    @mock.patch('website.views.use_ember_app')
    def test_preprint_provider_with_domain_without_redirect(self, mock_use_ember_app):
        domain = 'https://test.com/'
        provider = PreprintProviderFactory(_id='test', domain=domain, domain_redirect_enabled=False)
        preprint = PreprintFactory(provider=provider)
        url = web_url_for('resolve_guid', _guid=True, guid=preprint._id)
        res = self.app.get(url)
        mock_use_ember_app.assert_called_with()

    def test_preprint_provider_with_domain_with_redirect(self):
        domain = 'https://test.com/'
        provider = PreprintProviderFactory(_id='test', domain=domain, domain_redirect_enabled=True)
        preprint = PreprintFactory(provider=provider)
        url = web_url_for('resolve_guid', _guid=True, guid=preprint._id)
        res = self.app.get(url)

        assert_is_redirect(res)
        assert res.status_code == 301
        assert res.headers['location'] == f'{domain}{preprint._id}/'
        assert res.request.path == f'/{preprint._id}/'

    @mock.patch('website.views.use_ember_app')
    def test_preprint_provider_with_osf_domain(self, mock_use_ember_app):
        provider = PreprintProviderFactory(_id='osf', domain='https://osf.io/')
        preprint = PreprintFactory(provider=provider)
        url = web_url_for('resolve_guid', _guid=True, guid=preprint._id)
        res = self.app.get(url)
        mock_use_ember_app.assert_called_with()
