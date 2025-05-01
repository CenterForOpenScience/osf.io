import pytest

from api.base.settings.defaults import API_BASE
from osf_tests.factories import (
    ProjectFactory,
    AuthUserFactory,
)
from osf.utils.permissions import WRITE

@pytest.fixture()
def non_contributor():
    return AuthUserFactory()

@pytest.fixture()
def admin_contributor():
    return AuthUserFactory()

@pytest.fixture()
def write_contributor():
    return AuthUserFactory()

@pytest.fixture()
def project(admin_contributor, write_contributor):
    project = ProjectFactory(
        creator=admin_contributor
    )
    project.add_contributor(write_contributor, WRITE)
    return project


@pytest.mark.django_db
class TestNodeContributorsAndGroupMembers:
    def test_list_and_filter_contributors_and_group_members(
            self, app, project, admin_contributor, write_contributor,
            non_contributor):
        url = f'/{API_BASE}nodes/{project._id}/contributors_and_group_members/'

        # unauthenticated
        res = app.get(url, expect_errors=True)
        assert res.status_code == 401

        # noncontributor
        res = app.get(url, auth=non_contributor.auth, expect_errors=True)
        assert res.status_code == 403

        # write_contributor
        res = app.get(url, auth=write_contributor.auth, expect_errors=True)
        assert res.status_code == 200

        # assert all contributors and group members appear, no duplicates
        res = app.get(url, auth=admin_contributor.auth)
        assert res.status_code == 200
        assert res.content_type == 'application/vnd.api+json'
        assert len(res.json['data']) == 5
        expected = {
            admin_contributor._id,
            write_contributor._id,
        }
        actual = {node['id'] for node in res.json['data']}

        assert actual == expected

        url = f'/{API_BASE}nodes/{project._id}/contributors_and_group_members/?filter[given_name]=NOT_EVEN_A_NAME'
        res = app.get(url, auth=admin_contributor.auth)
        assert res.status_code == 200
        assert res.content_type == 'application/vnd.api+json'
        assert len(res.json['data']) == 0
