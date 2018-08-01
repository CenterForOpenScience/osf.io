import mock
import pytest

from addons.wiki.tests.factories import WikiFactory, WikiVersionFactory
from api.base.settings.defaults import API_BASE
from api_tests.wikis.views.test_wiki_detail import WikiCRUDTestCase
from framework.auth.core import Auth
from osf_tests.factories import (
    AuthUserFactory,
    ProjectFactory,
    RegistrationFactory,
)
from rest_framework import exceptions
from tests.base import fake

def update_payload(wiki_page, content):
    return {
        'data': {
            'id': wiki_page._id,
            'type': 'wiki-versions',
            'attributes': {
                'content': content
            }
        }
    }

@pytest.fixture()
def user():
    return AuthUserFactory()

@pytest.mark.django_db
class TestWikiVersionList:

    @pytest.fixture()
    def add_project_wiki_page(self):
        def add_page(node, user):
            with mock.patch('osf.models.AbstractNode.update_search'):
                wiki_page = WikiFactory(node=node, user=user)
                WikiVersionFactory(wiki_page=wiki_page, user=user)
                return wiki_page
        return add_page

    @pytest.fixture()
    def non_contrib(self):
        return AuthUserFactory()

    @pytest.fixture()
    def public_project(self, user):
        return ProjectFactory(is_public=True, creator=user)

    @pytest.fixture()
    def public_wiki(self, add_project_wiki_page, user, public_project):
        return add_project_wiki_page(public_project, user)

    @pytest.fixture()
    def public_url(self, public_project, public_wiki):
        return '/{}wikis/{}/versions/'.format(API_BASE, public_wiki._id)

    @pytest.fixture()
    def private_project(self, user):
        return ProjectFactory(creator=user)

    @pytest.fixture()
    def private_wiki(self, add_project_wiki_page, user, private_project):
        return add_project_wiki_page(private_project, user)

    @pytest.fixture()
    def private_url(self, private_project, private_wiki):
        return '/{}wikis/{}/versions/'.format(API_BASE, private_wiki._id)

    @pytest.fixture()
    def public_registration(self, user, public_project, public_wiki):
        public_registration = RegistrationFactory(project=public_project, user=user, is_public=True)
        return public_registration

    @pytest.fixture()
    def public_registration_url(self, public_registration):
        return '/{}wikis/{}/versions/'.format(API_BASE, public_registration.get_wiki_page('home')._id)

    @pytest.fixture()
    def private_registration(self, user, private_project, private_wiki):
        private_registration = RegistrationFactory(project=private_project, user=user)
        return private_registration

    @pytest.fixture()
    def private_registration_url(self, private_registration):
        return '/{}wikis/{}/versions/'.format(API_BASE, private_registration.get_wiki_page('home')._id)

    def test_return_wiki_versions(self, app, user, non_contrib, private_registration, public_wiki, private_wiki, public_url, private_url, private_registration_url):
        # test_return_public_node_wiki_versions_logged_out_user
        res = app.get(public_url)
        assert res.status_code == 200
        wiki_ids = [wiki['id'] for wiki in res.json['data']]
        assert str(public_wiki.get_version().identifier) in wiki_ids

        #   test_return_public_node_wiki_versions_logged_in_non_contributor
        res = app.get(public_url, auth=non_contrib.auth)
        assert res.status_code == 200
        wiki_ids = [wiki['id'] for wiki in res.json['data']]
        assert str(public_wiki.get_version().identifier) in wiki_ids

        #   test_return_public_node_wiki_versions_logged_in_contributor
        res = app.get(public_url, auth=user.auth)
        assert res.status_code == 200
        wiki_ids = [wiki['id'] for wiki in res.json['data']]
        assert str(public_wiki.get_version().identifier) in wiki_ids

        #   test_return_private_node_wiki_versions_logged_out_user
        res = app.get(private_url, expect_errors=True)
        assert res.status_code == 401
        assert res.json['errors'][0]['detail'] == exceptions.NotAuthenticated.default_detail

        #   test_return_private_node_wiki_versions_logged_in_non_contributor
        res = app.get(private_url, auth=non_contrib.auth, expect_errors=True)
        assert res.status_code == 403
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail

        #   test_return_private_node_wiki_versions_logged_in_contributor
        res = app.get(private_url, auth=user.auth)
        assert res.status_code == 200
        wiki_ids = [wiki['id'] for wiki in res.json['data']]
        assert str(private_wiki.get_version().identifier) in wiki_ids

        #   test_return_registration_wiki_versions_logged_out_user
        res = app.get(private_registration_url, expect_errors=True)
        assert res.status_code == 401
        assert res.json['errors'][0]['detail'] == exceptions.NotAuthenticated.default_detail

        #   test_return_registration_wiki_versions_logged_in_non_contributor
        res = app.get(private_registration_url, auth=non_contrib.auth, expect_errors=True)
        assert res.status_code == 403
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail

        #   test_return_registration_wiki_versions_logged_in_contributor
        res = app.get(private_registration_url, auth=user.auth)
        assert res.status_code == 200
        wiki_ids = [wiki['id'] for wiki in res.json['data']]
        assert str(private_registration.get_wiki_version('home').identifier) in wiki_ids

    def test_wiki_versions_not_returned_for_withdrawn_registration(self, app, user, private_registration, private_registration_url):
        private_registration.is_public = True
        withdrawal = private_registration.retract_registration(user=user, save=True)
        token = list(withdrawal.approval_state.values())[0]['approval_token']
        # TODO: Remove mocking when StoredFileNode is implemented
        with mock.patch('osf.models.AbstractNode.update_search'):
            withdrawal.approve_retraction(user, token)
            withdrawal.save()
        res = app.get(private_registration_url, auth=user.auth, expect_errors=True)
        assert res.status_code == 403
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail

    def test_relationship_links(self, app, user, public_project, private_project, public_wiki, private_wiki, public_registration, private_registration, public_url, private_url, public_registration_url, private_registration_url):

        #   test_public_node_wiki_versions_relationship_links
        res = app.get(public_url)
        expected_wiki_page_relationship_url = '{}wikis/{}/'.format(API_BASE, public_wiki._id)
        expected_user_relationship_url = '{}users/{}/'.format(API_BASE, user._id)
        assert expected_wiki_page_relationship_url in res.json['data'][0]['relationships']['wiki_page']['links']['related']['href']
        assert expected_user_relationship_url in res.json['data'][0]['relationships']['user']['links']['related']['href']

        #   test_private_node_wiki_versions_relationship_links
        res = app.get(private_url, auth=user.auth)
        expected_wiki_page_relationship_url = '{}wikis/{}/'.format(API_BASE, private_wiki._id)
        expected_user_relationship_url = '{}users/{}/'.format(API_BASE, user._id)
        assert expected_wiki_page_relationship_url in res.json['data'][0]['relationships']['wiki_page']['links']['related']['href']
        assert expected_user_relationship_url in res.json['data'][0]['relationships']['user']['links']['related']['href']

        #   test_public_registration_wiki_versions_relationship_links
        res = app.get(public_registration_url)
        expected_wiki_page_relationship_url = '{}wikis/{}/'.format(API_BASE, public_registration.get_wiki_page('home')._id)
        expected_user_relationship_url = '{}users/{}/'.format(API_BASE, user._id)
        assert expected_wiki_page_relationship_url in res.json['data'][0]['relationships']['wiki_page']['links']['related']['href']
        assert expected_user_relationship_url in res.json['data'][0]['relationships']['user']['links']['related']['href']

        #   test_private_registration_wiki_versions_relationship_links
        res = app.get(private_registration_url, auth=user.auth)
        expected_wiki_page_relationship_url = '{}wikis/{}/'.format(API_BASE, private_registration.get_wiki_page('home')._id)
        expected_user_relationship_url = '{}users/{}/'.format(API_BASE, user._id)
        assert expected_wiki_page_relationship_url in res.json['data'][0]['relationships']['wiki_page']['links']['related']['href']
        assert expected_user_relationship_url in res.json['data'][0]['relationships']['user']['links']['related']['href']

    def test_not_returned(self, app, public_project, public_registration, public_url, public_registration_url, public_wiki):

        #   test_registration_wiki_pages_not_returned_from_nodes_endpoint
        res = app.get(public_url)
        node_relationships = [
            node_wiki['relationships']['wiki_page']['links']['related']['href']
            for node_wiki in res.json['data']
        ]
        assert res.status_code == 200
        assert len(node_relationships) == 1
        assert public_wiki._id in node_relationships[0]

        #   test_node_wiki_pages_not_returned_from_registrations_endpoint
        res = app.get(public_registration_url)
        node_relationships = [
            node_wiki['relationships']['wiki_page']['links']['related']['href']
            for node_wiki in res.json['data']
        ]
        assert res.status_code == 200
        assert len(node_relationships) == 1
        assert public_registration.get_wiki_page('home')._id in node_relationships[0]

    def test_do_not_return_disabled_wiki(self, app, user, public_url, public_project):
        public_project.delete_addon('wiki', auth=Auth(user))
        res = app.get(public_url, expect_errors=True)
        assert res.status_code == 404


@pytest.mark.django_db
class TestWikiVersionCreate(WikiCRUDTestCase):

    @pytest.fixture()
    def url_wiki_versions_public(self, wiki_public):
        return '/{}wikis/{}/versions/'.format(API_BASE, wiki_public._id)

    @pytest.fixture()
    def url_wiki_versions_private(self, wiki_private):
        return '/{}wikis/{}/versions/'.format(API_BASE, wiki_private._id)

    @pytest.fixture()
    def url_wiki_versions_registration_public(self, wiki_registration_public):
        return '/{}wikis/{}/versions/'.format(API_BASE, wiki_registration_public._id)

    @pytest.fixture()
    def url_wiki_versions_registration_private(self, wiki_registration_private):
        return '/{}wikis/{}/versions/'.format(API_BASE, wiki_registration_private._id)

    def test_update_public_wiki_page_as_contributor(
        self, app, user_write_contributor, wiki_public,
        url_wiki_versions_public
    ):
        new_content = fake.text()
        res = app.post_json_api(
            url_wiki_versions_public,
            update_payload(wiki_public, new_content),
            auth=user_write_contributor.auth
        )
        wiki_public.reload()
        assert res.status_code == 201
        assert wiki_public.get_version().content == new_content

    def test_do_not_update_public_wiki_page(
        self, app, wiki_public,
        user_read_contributor, user_non_contributor,
        url_wiki_versions_public
    ):
        payload = update_payload(wiki_public, fake.text())

        # test_do_not_update_public_wiki_page_as_read_contributor
        res = app.post_json_api(
            url_wiki_versions_public,
            payload,
            auth=user_read_contributor.auth,
            expect_errors=True
        )
        assert res.status_code == 403

        # test_do_not_update_public_wiki_page_as_non_contributor
        res = app.post_json_api(
            url_wiki_versions_public,
            payload,
            auth=user_non_contributor.auth,
            expect_errors=True
        )
        assert res.status_code == 403

        # test_do_not_update_public_wiki_page_unauthenticated
        res = app.post_json_api(
            url_wiki_versions_public,
            payload,
            expect_errors=True
        )
        assert res.status_code == 401

    def test_update_private_wiki_page(
        self, app, wiki_private,
        user_write_contributor, url_wiki_versions_private
    ):
        new_content = fake.text()
        res = app.post_json_api(
            url_wiki_versions_private,
            update_payload(wiki_private, new_content),
            auth=user_write_contributor.auth
        )
        wiki_private.reload()
        assert res.status_code == 201
        assert wiki_private.get_version().content == new_content

    def test_do_not_update_private_wiki_page(
        self, app, wiki_private,
        user_read_contributor, user_non_contributor,
        url_wiki_versions_private
    ):
        payload = update_payload(wiki_private, fake.text())

        # test_do_not_update_private_wiki_page_as_read_contributor
        res = app.post_json_api(
            url_wiki_versions_private,
            payload,
            auth=user_read_contributor.auth,
            expect_errors=True
        )
        assert res.status_code == 403

        # test_do_not_update_private_wiki_page_as_non_contributor
        res = app.post_json_api(
            url_wiki_versions_private,
            payload,
            auth=user_non_contributor.auth,
            expect_errors=True
        )
        assert res.status_code == 403

        # test_do_not_update_private_wiki_page_unauthenticated
        res = app.post_json_api(
            url_wiki_versions_private,
            payload,
            expect_errors=True
        )
        assert res.status_code == 401

    def test_do_not_update_wiki_on_registrations(
        self, app, user_creator,
        wiki_registration_public, wiki_registration_private,
        url_wiki_versions_registration_public, url_wiki_versions_registration_private
    ):
        # test_do_not_update_wiki_on_public_registration
        res = app.post_json_api(
            url_wiki_versions_registration_public,
            update_payload(wiki_registration_public, fake.text()),
            auth=user_creator.auth,
            expect_errors=True
        )
        assert res.status_code == 405

        # test_do_not_update_wiki_on_private_registration
        res = app.post_json_api(
            url_wiki_versions_registration_private,
            update_payload(wiki_registration_private, fake.text()),
            auth=user_creator.auth,
            expect_errors=True
        )
        assert res.status_code == 405

    def test_do_not_update_disabled_public_wiki_page(
        self, app, user_creator, wiki_public,
        project_public, url_wiki_versions_public
    ):
        project_public.delete_addon('wiki', auth=Auth(user_creator))
        new_content = fake.text()
        res = app.post_json_api(
            url_wiki_versions_public,
            update_payload(wiki_public, new_content),
            auth=user_creator.auth,
            expect_errors=True
        )
        assert res.status_code == 404

    def test_update_wiki_page_if_publicly_editable_non_contrib(
        self, app, user_creator, user_non_contributor,
        project_public, url_wiki_versions_public, wiki_public
    ):
        project_public.addons_wiki_node_settings.set_editing(True, auth=Auth(user_creator))
        new_content = fake.text()
        res = app.post_json_api(
            url_wiki_versions_public,
            update_payload(wiki_public, new_content),
            auth=user_non_contributor.auth
        )
        assert res.status_code == 201
