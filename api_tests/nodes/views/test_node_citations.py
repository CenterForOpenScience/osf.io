import pytest

from api.base.settings.defaults import API_BASE
from framework.auth.core import Auth
from rest_framework import exceptions
from osf_tests.factories import (
    ProjectFactory,
    AuthUserFactory,
)


@pytest.fixture()
def admin_contributor():
    return AuthUserFactory()


@pytest.fixture()
def write_contrib():
    return AuthUserFactory()


@pytest.fixture()
def read_contrib():
    return AuthUserFactory()


@pytest.fixture()
def non_contrib():
    return AuthUserFactory()


@pytest.fixture()
def disabled_contrib():
    # disabled in the disable_user fixture so that they can be added as a
    # contributor first
    return AuthUserFactory()


@pytest.fixture()
def public_project(admin_contributor):
    return ProjectFactory(creator=admin_contributor, is_public=True)


@pytest.fixture()
def private_project(
        admin_contributor, write_contrib,
        read_contrib, disabled_contrib):
    private_project = ProjectFactory(creator=admin_contributor)
    private_project.add_contributor(
        write_contrib,
        permissions=['read', 'write'],
        auth=Auth(admin_contributor))
    private_project.add_contributor(
        read_contrib,
        permissions=['read'],
        auth=Auth(admin_contributor))
    private_project.add_contributor(
        disabled_contrib,
        permissions=['read'],
        auth=Auth(admin_contributor))
    private_project.save()
    return private_project


@pytest.fixture()
def disable_user(disabled_contrib, private_project):
    # pass private_project so that account is disabled after private_project
    # is setup
    disabled_contrib.disable_account()
    disabled_contrib.is_registered = False
    disabled_contrib.save()


@pytest.mark.django_db
class NodeCitationsMixin:

    def test_node_citations(
            self, app, admin_contributor,
            write_contrib, read_contrib,
            non_contrib, private_url, public_url
    ):

        #   test_admin_can_view_private_project_citations
        res = app.get(private_url, auth=admin_contributor.auth)
        assert res.status_code == 200

    #   test_write_contrib_can_view_private_project_citations
        res = app.get(private_url, auth=write_contrib.auth)
        assert res.status_code == 200

    #   test_read_contrib_can_view_private_project_citations
        res = app.get(private_url, auth=read_contrib.auth)
        assert res.status_code == 200

    #   test_non_contrib_cannot_view_private_project_citations
        res = app.get(private_url, auth=non_contrib.auth, expect_errors=True)
        assert res.status_code == 403
        assert res.json['errors'][0]['detail'] == exceptions.PermissionDenied.default_detail

    #   test_unauthenticated_cannot_view_private_project_citations
        res = app.get(private_url, expect_errors=True)
        assert res.status_code == 401
        assert res.json['errors'][0]['detail'] == exceptions.NotAuthenticated.default_detail

    #   test_unauthenticated_can_view_public_project_citations
        res = app.get(public_url)
        assert res.status_code == 200


class TestNodeCitations(NodeCitationsMixin):
    @pytest.fixture()
    def public_url(self, public_project):
        return '/{}nodes/{}/citation/'.format(API_BASE, public_project._id)

    @pytest.fixture()
    def private_url(self, private_project):
        return '/{}nodes/{}/citation/'.format(API_BASE, private_project._id)

    @pytest.fixture()
    def payload(self):
        return {
            'data': {
                'attributes': {
                    'custom_citation_text': 'SB52-41-33/Weapon-X-HOF'
                }
            }
        }

    def test_node_add_custom_citation(self, app, admin_contributor, read_contrib, public_url, public_project, payload):

        res = app.put_json_api(public_url, payload, expect_errors=True)
        assert res.status_code == 401
        assert res.json['errors'][0]['detail'] == 'Authentication credentials were not provided.'

        res = app.put_json_api(public_url, payload, auth=read_contrib.auth, expect_errors=True)
        assert res.status_code == 403
        assert res.json['errors'][0]['detail'] == 'You do not have permission to perform this action.'

        res = app.put_json_api(public_url, payload, auth=admin_contributor.auth)
        assert res.status_code == 200
        assert res.json['data']['attributes']['custom_citation_text'] == 'SB52-41-33/Weapon-X-HOF'

        public_project.reload()
        assert public_project.custom_citation_text == 'SB52-41-33/Weapon-X-HOF'
        assert public_project.logs.first().action == 'custom_citation_added'

    def test_node_edit_custom_citation(self, app, admin_contributor, public_url, public_project, payload):
        public_project.custom_citation_text = 'TheElderSporles'
        public_project.save()

        res = app.put_json_api(public_url, payload, auth=admin_contributor.auth)
        assert res.status_code == 200
        assert res.json['data']['attributes']['custom_citation_text'] == 'SB52-41-33/Weapon-X-HOF'

        public_project.reload()
        assert public_project.custom_citation_text == 'SB52-41-33/Weapon-X-HOF'
        assert public_project.logs.first().action == 'custom_citation_edited'

    def test_node_remove_custom_citation(self, app, admin_contributor, public_url, public_project, payload):
        public_project.custom_citation_text = 'TheElderSporles'
        public_project.save()
        payload['data']['attributes']['custom_citation_text'] = ''

        res = app.put_json_api(public_url, payload, auth=admin_contributor.auth, expect_errors=True)
        assert res.status_code == 200
        public_project.reload()
        assert public_project.custom_citation_text == ''
        assert public_project.logs.first().action == 'custom_citation_removed'

    def test_node_citations_errors(self, app, admin_contributor, public_url):

        #   test_citations_are_read_only
        post_res = app.post_json_api(
            public_url, {},
            auth=admin_contributor.auth,
            expect_errors=True)
        assert post_res.status_code == 405
        delete_res = app.delete_json_api(
            public_url,
            auth=admin_contributor.auth,
            expect_errors=True)
        assert delete_res.status_code == 405


class TestNodeCitationsStyle(NodeCitationsMixin):
    @pytest.fixture()
    def public_url(self, public_project):
        return '/{}nodes/{}/citation/apa/'.format(API_BASE, public_project._id)

    @pytest.fixture()
    def private_url(self, private_project):
        return '/{}nodes/{}/citation/apa/'.format(
            API_BASE, private_project._id)

    def test_node_citations_errors(self, app, admin_contributor, public_url):

        #   test_citations_are_read_only
        post_res = app.post_json_api(
            public_url, {},
            auth=admin_contributor.auth,
            expect_errors=True)
        assert post_res.status_code == 405
        put_res = app.put_json_api(
            public_url, {},
            auth=admin_contributor.auth,
            expect_errors=True)
        assert put_res.status_code == 405
        delete_res = app.delete_json_api(
            public_url,
            auth=admin_contributor.auth,
            expect_errors=True)
        assert delete_res.status_code == 405
