import mock
import pytest
import furl
import pytz
import datetime
from future.moves.urllib.parse import urlparse
from nose.tools import *  # noqa:

from addons.wiki.models import WikiPage
from addons.wiki.tests.factories import (
    WikiFactory,
    WikiVersionFactory,
)

from api.base.settings.defaults import API_BASE
from framework.auth.core import Auth

from osf.models import Guid
from osf.utils import permissions
from osf_tests.factories import (
    AuthUserFactory,
    CommentFactory,
    PrivateLinkFactory,
    ProjectFactory,
    RegistrationFactory,
)
from tests.base import ApiWikiTestCase, fake


def make_rename_payload(wiki_page):
    new_page_name = fake.word()
    payload = {
        'data': {
            'id': wiki_page._id,
            'type': 'wikis',
            'attributes': {
                'name': new_page_name
            }
        }
    }
    return payload, new_page_name


@pytest.mark.django_db
class WikiCRUDTestCase:

    @pytest.fixture()
    def user_creator(self):
        return AuthUserFactory()

    @pytest.fixture()
    def project_public(self, user_creator):
        project_public = ProjectFactory(
            is_public=True,
            creator=user_creator
        )
        wiki_page = WikiFactory(node=project_public, user=user_creator)
        WikiVersionFactory(wiki_page=wiki_page, user=user_creator)
        return project_public

    @pytest.fixture()
    def project_private(self, user_creator):
        project_private = ProjectFactory(
            is_public=False,
            creator=user_creator
        )
        wiki_page = WikiFactory(node=project_private, user=user_creator)
        WikiVersionFactory(wiki_page=wiki_page, user=user_creator)
        return project_private

    @pytest.fixture()
    def user_non_contributor(self):
        return AuthUserFactory()

    @pytest.fixture()
    def user_write_contributor(self, project_public, project_private):
        user = AuthUserFactory()
        project_public.add_contributor(user, permissions=permissions.WRITE)
        project_private.add_contributor(user, permissions=permissions.WRITE)
        return user

    @pytest.fixture()
    def user_read_contributor(self, project_public, project_private):
        user = AuthUserFactory()
        project_public.add_contributor(user, permissions=permissions.READ)
        project_private.add_contributor(user, permissions=permissions.READ)
        return user

    @pytest.fixture()
    def wiki_public(self, project_public, user_creator):
        wiki_page = WikiFactory(node=project_public, user=user_creator, page_name=fake.word())
        WikiVersionFactory(wiki_page=wiki_page, user=user_creator)
        return wiki_page

    @pytest.fixture()
    def wiki_private(self, project_private, user_creator):
        wiki_page = WikiFactory(node=project_private, user=user_creator, page_name=fake.word())
        WikiVersionFactory(wiki_page=wiki_page, user=user_creator)
        return wiki_page

    @pytest.fixture()
    def wiki_publicly_editable(self, project_public, user_creator):
        pass

    @pytest.fixture()
    def wiki_registration_public(self, project_public, user_creator):
        registration = RegistrationFactory(project=project_public, is_public=True)
        wiki_page = WikiFactory(node=registration, user=user_creator, page_name=fake.word())
        WikiVersionFactory(wiki_page=wiki_page, user=user_creator)
        return wiki_page

    @pytest.fixture()
    def wiki_registration_private(self, project_public, user_creator):
        registration = RegistrationFactory(project=project_public, is_public=False)
        wiki_page = WikiFactory(node=registration, user=user_creator, page_name=fake.word())
        WikiVersionFactory(wiki_page=wiki_page, user=user_creator)
        return wiki_page

    @pytest.fixture()
    def url_wiki_public(self, wiki_public):
        return '/{}wikis/{}/'.format(API_BASE, wiki_public._id)

    @pytest.fixture()
    def url_wiki_home(self, project_public):
        wiki_home = project_public.wikis.get(page_name='home')
        return '/{}wikis/{}/'.format(API_BASE, wiki_home._id)

    @pytest.fixture()
    def url_wiki_private(self, wiki_private):
        return '/{}wikis/{}/'.format(API_BASE, wiki_private._id)

    @pytest.fixture()
    def url_wiki_publicly_editable(self, wiki_publicly_editable):
        # return '/{}wikis/{}/'.format(API_BASE, wiki_publicly_editable._id)
        pass

    @pytest.fixture()
    def url_registration_wiki_public(self, wiki_registration_public):
        return '/{}wikis/{}/'.format(API_BASE, wiki_registration_public._id)

    @pytest.fixture()
    def url_registration_wiki_private(self, wiki_registration_private):
        return '/{}wikis/{}/'.format(API_BASE, wiki_registration_private._id)


class TestWikiDetailView(ApiWikiTestCase):

    def _set_up_public_project_with_wiki_page(self, project_options=None):
        project_options = project_options or {}
        self.public_project = ProjectFactory(is_public=True, creator=self.user, **project_options)
        from addons.wiki.tests.factories import WikiFactory, WikiVersionFactory
        with mock.patch('osf.models.AbstractNode.update_search'):
            self.public_wiki_page = WikiFactory(node=self.public_project, user=self.user)
            self.public_wiki = WikiVersionFactory(wiki_page=self.public_wiki_page, user=self.user)
        self.public_url = '/{}wikis/{}/'.format(API_BASE, self.public_wiki_page._id)
        return self.public_wiki_page

    def _set_up_private_project_with_wiki_page(self):
        self.private_project = ProjectFactory(creator=self.user)
        self.private_wiki = self._add_project_wiki_page(
            self.private_project, self.user)
        self.private_url = '/{}wikis/{}/'.format(
            API_BASE, self.private_wiki._id)

    def _set_up_public_registration_with_wiki_page(self):
        self._set_up_public_project_with_wiki_page()
        self.public_registration = RegistrationFactory(
            project=self.public_project, user=self.user, is_public=True)
        self.public_registration_wiki_id = WikiPage.objects.get_for_node(self.public_registration, 'home')._id
        self.public_registration.save()
        self.public_registration_url = '/{}wikis/{}/'.format(
            API_BASE, self.public_registration_wiki_id)

    def _set_up_private_registration_with_wiki_page(self):
        self._set_up_private_project_with_wiki_page()
        self.private_registration = RegistrationFactory(
            project=self.private_project, user=self.user)
        self.private_registration_wiki_id = WikiPage.objects.get_for_node(self.private_registration, 'home')._id
        self.private_registration.save()
        self.private_registration_url = '/{}wikis/{}/'.format(
            API_BASE, self.private_registration_wiki_id)

    def test_public_node_logged_out_user_can_view_wiki(self):
        self._set_up_public_project_with_wiki_page()
        res = self.app.get(self.public_url)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['id'], self.public_wiki_page._id)

    def test_public_node_logged_in_non_contributor_can_view_wiki(self):
        self._set_up_public_project_with_wiki_page()
        res = self.app.get(self.public_url, auth=self.non_contributor.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['id'], self.public_wiki_page._id)

    def test_public_node_logged_in_contributor_can_view_wiki(self):
        self._set_up_public_project_with_wiki_page()
        res = self.app.get(self.public_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['id'], self.public_wiki_page._id)

    def test_private_node_logged_out_user_cannot_view_wiki(self):
        self._set_up_private_project_with_wiki_page()
        res = self.app.get(self.private_url, expect_errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(res.json['errors'][0]['detail'],
                     'Authentication credentials were not provided.')

    def test_private_node_logged_in_non_contributor_cannot_view_wiki(self):
        self._set_up_private_project_with_wiki_page()
        res = self.app.get(
            self.private_url,
            auth=self.non_contributor.auth,
            expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(
            res.json['errors'][0]['detail'],
            'You do not have permission to perform this action.')

    def test_private_node_logged_in_contributor_can_view_wiki(self):
        self._set_up_private_project_with_wiki_page()
        res = self.app.get(self.private_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['id'], self.private_wiki._id)

    def test_private_node_user_with_anonymous_link_can_view_wiki(self):
        self._set_up_private_project_with_wiki_page()
        private_link = PrivateLinkFactory(anonymous=True)
        private_link.nodes.add(self.private_project)
        private_link.save()
        url = furl.furl(
            self.private_url).add(
            query_params={
                'view_only': private_link.key}).url
        res = self.app.get(url)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['id'], self.private_wiki._id)

    def test_private_node_user_with_view_only_link_can_view_wiki(self):
        self._set_up_private_project_with_wiki_page()
        private_link = PrivateLinkFactory(anonymous=False)
        private_link.nodes.add(self.private_project)
        private_link.save()
        url = furl.furl(
            self.private_url).add(
            query_params={
                'view_only': private_link.key}).url
        res = self.app.get(url)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['id'], self.private_wiki._id)

    def test_public_registration_logged_out_user_cannot_view_wiki(self):
        self._set_up_public_registration_with_wiki_page()
        res = self.app.get(self.public_registration_url, expect_errors=True)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['id'], self.public_registration_wiki_id)

    def test_public_registration_logged_in_non_contributor_cannot_view_wiki(
            self):
        self._set_up_public_registration_with_wiki_page()
        res = self.app.get(
            self.public_registration_url,
            auth=self.non_contributor.auth,
            expect_errors=True)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['id'], self.public_registration_wiki_id)

    def test_public_registration_contributor_can_view_wiki(self):
        self._set_up_public_registration_with_wiki_page()
        res = self.app.get(self.public_registration_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['id'], self.public_registration_wiki_id)

    def test_user_cannot_view_withdrawn_registration_wikis(self):
        self._set_up_public_registration_with_wiki_page()
        # TODO: Remove mocking when StoredFileNode is implemented
        with mock.patch('osf.models.AbstractNode.update_search'):
            withdrawal = self.public_registration.retract_registration(
                user=self.user, save=True)
            token = withdrawal.approval_state.values()[0]['approval_token']
            withdrawal.approve_retraction(self.user, token)
            withdrawal.save()
        res = self.app.get(
            self.public_registration_url,
            auth=self.user.auth,
            expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(
            res.json['errors'][0]['detail'],
            'You do not have permission to perform this action.')

    def test_private_registration_logged_out_user_cannot_view_wiki(self):
        self._set_up_private_registration_with_wiki_page()
        res = self.app.get(self.private_registration_url, expect_errors=True)
        assert_equal(res.status_code, 401)
        assert_equal(res.json['errors'][0]['detail'],
                     'Authentication credentials were not provided.')

    def test_private_registration_logged_in_non_contributor_cannot_view_wiki(
            self):
        self._set_up_private_registration_with_wiki_page()
        res = self.app.get(
            self.private_registration_url,
            auth=self.non_contributor.auth,
            expect_errors=True)
        assert_equal(res.status_code, 403)
        assert_equal(
            res.json['errors'][0]['detail'],
            'You do not have permission to perform this action.')

    def test_private_registration_contributor_can_view_wiki(self):
        self._set_up_private_registration_with_wiki_page()
        res = self.app.get(self.private_registration_url, auth=self.user.auth)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data']['id'], self.private_registration_wiki_id)

    def test_wiki_has_user_link(self):
        self._set_up_public_project_with_wiki_page()
        res = self.app.get(self.public_url)
        url = res.json['data']['relationships']['user']['links']['related']['href']
        expected_url = '/{}users/{}/'.format(API_BASE, self.user._id)
        assert_equal(res.status_code, 200)
        assert_equal(urlparse(url).path, expected_url)

    def test_wiki_has_node_link(self):
        self._set_up_public_project_with_wiki_page()
        res = self.app.get(self.public_url)
        url = res.json['data']['relationships']['node']['links']['related']['href']
        expected_url = '/{}nodes/{}/'.format(API_BASE, self.public_project._id)
        assert_equal(res.status_code, 200)
        assert_equal(urlparse(url).path, expected_url)

    def test_wiki_has_comments_link(self):
        self._set_up_public_project_with_wiki_page()
        res = self.app.get(self.public_url)
        assert_equal(res.status_code, 200)
        url = res.json['data']['relationships']['comments']['links']['related']['href']
        CommentFactory(
            node=self.public_project,
            target=Guid.load(
                self.public_wiki_page._id),
            user=self.user)
        res = self.app.get(url)
        assert_equal(res.status_code, 200)
        assert_equal(res.json['data'][0]['type'], 'comments')

    def test_only_project_contrib_can_comment_on_closed_project(self):
        self._set_up_public_project_with_wiki_page(
            project_options={'comment_level': 'private'})
        res = self.app.get(self.public_url, auth=self.user.auth)
        can_comment = res.json['data']['attributes']['current_user_can_comment']
        assert_equal(res.status_code, 200)
        assert_equal(can_comment, True)

        res = self.app.get(self.public_url, auth=self.non_contributor.auth)
        can_comment = res.json['data']['attributes']['current_user_can_comment']
        assert_equal(res.status_code, 200)
        assert_equal(can_comment, False)

    def test_any_loggedin_user_can_comment_on_open_project(self):
        self._set_up_public_project_with_wiki_page(
            project_options={'comment_level': 'public'})
        res = self.app.get(self.public_url, auth=self.non_contributor.auth)
        can_comment = res.json['data']['attributes']['current_user_can_comment']
        assert_equal(res.status_code, 200)
        assert_equal(can_comment, True)

    def test_non_logged_in_user_cant_comment(self):
        self._set_up_public_project_with_wiki_page(
            project_options={'comment_level': 'public'})
        res = self.app.get(self.public_url)
        can_comment = res.json['data']['attributes']['current_user_can_comment']
        assert_equal(res.status_code, 200)
        assert_equal(can_comment, False)

    def test_wiki_has_download_link(self):
        self._set_up_public_project_with_wiki_page()
        res = self.app.get(self.public_url)
        url = res.json['data']['links']['download']
        expected_url = '/{}wikis/{}/content/'.format(
            API_BASE, self.public_wiki_page._id)
        assert_equal(res.status_code, 200)
        assert_in(expected_url, url)

    def test_wiki_invalid_id_not_found(self):
        url = '/{}wikis/{}/'.format(API_BASE, 'abcde')
        res = self.app.get(url, expect_errors=True)
        assert_equal(res.status_code, 404)

    def test_deleted_wiki_not_returned(self):
        self._set_up_public_project_with_wiki_page()
        url = '/{}wikis/{}/'.format(
            API_BASE, self.public_wiki_page._id)
        res = self.app.get(url)
        assert_equal(res.status_code, 200)
        self.public_wiki_page.deleted = datetime.datetime(2017, 3, 16, 11, 00, tzinfo=pytz.utc)
        self.public_wiki_page.save()

        res = self.app.get(url, expect_errors=True)
        assert_equal(res.status_code, 410)

    def test_public_node_wiki_relationship_links(self):
        self._set_up_public_project_with_wiki_page()
        res = self.app.get(self.public_url)
        expected_nodes_relationship_url = '{}nodes/{}/'.format(
            API_BASE, self.public_project._id)
        expected_comments_relationship_url = '{}nodes/{}/comments/'.format(
            API_BASE, self.public_project._id)
        assert_in(
            expected_nodes_relationship_url,
            res.json['data']['relationships']['node']['links']['related']['href'])
        assert_in(
            expected_comments_relationship_url,
            res.json['data']['relationships']['comments']['links']['related']['href'])

    def test_private_node_wiki_relationship_links(self):
        self._set_up_private_project_with_wiki_page()
        res = self.app.get(self.private_url, auth=self.user.auth)
        expected_nodes_relationship_url = '{}nodes/{}/'.format(
            API_BASE, self.private_project._id)
        expected_comments_relationship_url = '{}nodes/{}/comments/'.format(
            API_BASE, self.private_project._id)
        assert_in(
            expected_nodes_relationship_url,
            res.json['data']['relationships']['node']['links']['related']['href'])
        assert_in(
            expected_comments_relationship_url,
            res.json['data']['relationships']['comments']['links']['related']['href'])

    def test_public_registration_wiki_relationship_links(self):
        self._set_up_public_registration_with_wiki_page()
        res = self.app.get(self.public_registration_url)
        expected_nodes_relationship_url = '{}registrations/{}/'.format(
            API_BASE, self.public_registration._id)
        expected_comments_relationship_url = '{}registrations/{}/comments/'.format(
            API_BASE, self.public_registration._id)
        assert_in(
            expected_nodes_relationship_url,
            res.json['data']['relationships']['node']['links']['related']['href'])
        assert_in(
            expected_comments_relationship_url,
            res.json['data']['relationships']['comments']['links']['related']['href'])

    def test_private_registration_wiki_relationship_links(self):
        self._set_up_private_registration_with_wiki_page()
        res = self.app.get(self.private_registration_url, auth=self.user.auth)
        expected_nodes_relationship_url = '{}registrations/{}/'.format(
            API_BASE, self.private_registration._id)
        expected_comments_relationship_url = '{}registrations/{}/comments/'.format(
            API_BASE, self.private_registration._id)
        assert_in(
            expected_nodes_relationship_url,
            res.json['data']['relationships']['node']['links']['related']['href'])
        assert_in(
            expected_comments_relationship_url,
            res.json['data']['relationships']['comments']['links']['related']['href'])

    def test_do_not_return_disabled_wiki(self):
        self._set_up_public_project_with_wiki_page()
        self.public_project.delete_addon('wiki', auth=Auth(self.user))
        res = self.app.get(self.public_url, expect_errors=True)
        assert res.status_code == 404


@pytest.mark.django_db
class TestWikiDelete(WikiCRUDTestCase):

    def test_delete_public_wiki_page(
        self, app, user_write_contributor, url_wiki_public
    ):
        res = app.delete(url_wiki_public, auth=user_write_contributor.auth)
        assert res.status_code == 204

    def test_do_not_delete_public_wiki_page(
        self, app, user_creator, user_read_contributor, user_non_contributor,
        url_wiki_public, url_wiki_home, url_wiki_publicly_editable
    ):
        # test_do_not_delete_home_wiki_page
        res = app.delete(url_wiki_home, auth=user_creator.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'The home wiki page cannot be deleted.'

        # test_do_not_delete_public_wiki_page_as_read_contributor
        res = app.delete(url_wiki_public, auth=user_read_contributor.auth, expect_errors=True)
        assert res.status_code == 403

        # test_do_not_delete_public_wiki_page_as_non_contributor
        res = app.delete(url_wiki_public, auth=user_non_contributor.auth, expect_errors=True)
        assert res.status_code == 403

        # test_do_not_delete_public_wiki_page_as_unauthenticated
        res = app.delete(url_wiki_public, expect_errors=True)
        assert res.status_code == 401

    def test_delete_private_wiki_page(self, app, user_write_contributor, url_wiki_private):
        res = app.delete(url_wiki_private, auth=user_write_contributor.auth)
        assert res.status_code == 204

    def test_do_not_delete_private_wiki_page(
        self, app, user_read_contributor, user_non_contributor, url_wiki_private
    ):
        # test_do_not_delete_private_wiki_page_as_read_contributor
        res = app.delete(url_wiki_private, auth=user_read_contributor.auth, expect_errors=True)
        assert res.status_code == 403

        # test_do_not_delete_private_wiki_page_as_non_contributor
        res = app.delete(url_wiki_private, auth=user_non_contributor.auth, expect_errors=True)
        assert res.status_code == 403

        # test_do_not_delete_private_wiki_page_as_unauthenticated
        res = app.delete(url_wiki_private, expect_errors=True)
        assert res.status_code == 401

    def test_do_not_delete_registration_wiki_page(
        self, app, user_creator,
        url_registration_wiki_public, url_registration_wiki_private
    ):
        # test_do_not_delete_wiki_on_public_registration
        res = app.delete(url_registration_wiki_public, auth=user_creator.auth, expect_errors=True)
        assert res.status_code == 405

        # test_do_not_delete_wiki_on_embargoed_registration
        res = app.delete(url_registration_wiki_private, auth=user_creator.auth, expect_errors=True)
        assert res.status_code == 405


@pytest.mark.django_db
class TestWikiUpdate(WikiCRUDTestCase):

    def test_rename_public_wiki_page(
        self, app, user_write_contributor, url_wiki_public, wiki_public
    ):
        payload, new_name = make_rename_payload(wiki_public)
        res = app.patch_json_api(url_wiki_public, payload, auth=user_write_contributor.auth)
        assert res.status_code == 200
        assert res.json['data']['attributes']['name'] == new_name

    def test_do_not_update_content_public_wiki_page(
        self, app, user_write_contributor, url_wiki_public, wiki_public
    ):
        res = app.patch_json_api(
            url_wiki_public,
            {
                'data': {
                    'id': wiki_public._id,
                    'type': 'wikis',
                    'attributes': {
                        'name': 'new page name',
                        'content': 'brave new wiki'
                    }
                }
            },
            auth=user_write_contributor.auth
        )
        assert res.status_code == 200
        assert wiki_public.get_version().content != 'brave new wiki'

    def test_do_not_rename_public_wiki_page(
        self, app, wiki_public, project_public,
        user_creator, user_read_contributor, user_non_contributor,
        url_wiki_public, url_wiki_home, url_wiki_publicly_editable
    ):
        # test_do_not_rename_home_wiki_page
        wiki_home = project_public.wikis.get(page_name='home')
        payload, _ = make_rename_payload(wiki_home)
        res = app.patch_json_api(url_wiki_home, payload, auth=user_creator.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Cannot rename wiki home page'

        # test_do_not_rename_public_wiki_page_as_read_contributor
        payload, _ = make_rename_payload(wiki_public)
        res = app.patch_json_api(url_wiki_public, payload, auth=user_read_contributor.auth, expect_errors=True)
        assert res.status_code == 403

        # test_do_not_rename_public_wiki_page_as_non_contributor
        res = app.patch_json_api(url_wiki_public, payload, auth=user_non_contributor.auth, expect_errors=True)
        assert res.status_code == 403

        # test_do_not_rename_public_wiki_page_as_unauthenticated
        res = app.patch_json_api(url_wiki_public, payload, expect_errors=True)
        assert res.status_code == 401

    def test_rename_private_wiki_page(
        self, app, user_write_contributor, wiki_private, url_wiki_private
    ):
        payload, new_name = make_rename_payload(wiki_private)
        res = app.patch_json_api(url_wiki_private, payload, auth=user_write_contributor.auth)
        assert res.status_code == 200
        assert res.json['data']['attributes']['name'] == new_name

    def test_do_not_rename_private_wiki_page(
        self, app, wiki_private,
        user_read_contributor, user_non_contributor, url_wiki_private
    ):
        # test_do_not_rename_public_wiki_page_as_read_contributor
        payload, _ = make_rename_payload(wiki_private)
        res = app.patch_json_api(url_wiki_private, payload, auth=user_read_contributor.auth, expect_errors=True)
        assert res.status_code == 403

        # test_do_not_rename_public_wiki_page_as_non_contributor
        res = app.patch_json_api(url_wiki_private, payload, auth=user_non_contributor.auth, expect_errors=True)
        assert res.status_code == 403

        # test_do_not_rename_public_wiki_page_as_unauthenticated
        res = app.patch_json_api(url_wiki_private, payload, expect_errors=True)
        assert res.status_code == 401

    def test_do_not_rename_registration_wiki_page(
        self, app, wiki_registration_public, wiki_registration_private,
        user_creator, url_registration_wiki_public, url_registration_wiki_private
    ):
        # test_do_not_rename_wiki_on_public_registration
        payload, _ = make_rename_payload(wiki_registration_public)
        res = app.patch_json_api(url_registration_wiki_public, payload, auth=user_creator.auth, expect_errors=True)
        assert res.status_code == 405

        # test_do_not_rename_wiki_on_embargoed_registration
        payload, _ = make_rename_payload(wiki_registration_private)
        res = app.patch_json_api(url_registration_wiki_private, payload, auth=user_creator.auth, expect_errors=True)
        assert res.status_code == 405
