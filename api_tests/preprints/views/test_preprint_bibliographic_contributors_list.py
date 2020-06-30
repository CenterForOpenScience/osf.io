import pytest

from api.base.settings.defaults import API_BASE
from osf_tests.factories import (
    PreprintFactory,
    AuthUserFactory,
)
from osf.utils.permissions import READ, WRITE, ADMIN


@pytest.mark.django_db
@pytest.mark.enable_quickfiles_creation
class TestNodeBibliographicContributors:
    @pytest.fixture()
    def admin_contributor_bib(self):
        return AuthUserFactory(given_name='Oranges')

    @pytest.fixture()
    def write_contributor_non_bib(self):
        return AuthUserFactory()

    @pytest.fixture()
    def read_contributor_bib(self):
        return AuthUserFactory(given_name='Grapes')

    @pytest.fixture()
    def non_contributor(self):
        return AuthUserFactory()

    @pytest.fixture()
    def preprint(self, admin_contributor_bib, write_contributor_non_bib, read_contributor_bib):
        preprint = PreprintFactory(
            creator=admin_contributor_bib
        )
        preprint.add_contributor(write_contributor_non_bib, WRITE, visible=False)
        preprint.add_contributor(read_contributor_bib, READ)
        preprint.save()
        return preprint

    @pytest.fixture()
    def url(self, preprint):
        return '/{}preprints/{}/bibliographic_contributors/'.format(API_BASE, preprint._id)

    def test_list_and_filter_bibliographic_contributors(self, app, url, preprint, admin_contributor_bib,
            write_contributor_non_bib, read_contributor_bib, non_contributor):

        # Test GET unauthenticated
        res = app.get(url)
        assert res.status_code == 200

        # Test GET non_contributor
        res = app.get(url, auth=non_contributor.auth)
        assert res.status_code == 200

        # Test GET read contrib
        res = app.get(url, auth=read_contributor_bib.auth, expect_errors=True)
        assert res.status_code == 200

        # Test GET write contrib
        res = app.get(url, auth=write_contributor_non_bib.auth, expect_errors=True)
        assert res.status_code == 200

        # Test POST not allowed
        res = app.post_json_api(url, auth=write_contributor_non_bib.auth, expect_errors=True)
        assert res.status_code == 405

        # Test GET contributor, only bibliographic contribs included
        res = app.get(url, auth=admin_contributor_bib.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == 2
        actual = [contrib['id'].split('-')[1] for contrib in res.json['data']]
        assert admin_contributor_bib._id in actual
        assert write_contributor_non_bib._id not in actual
        assert read_contributor_bib._id in actual

        # Test filter contributors on perms
        perm_filter = '{}?filter[permission]={}'.format(url, READ)
        res = app.get(perm_filter, auth=admin_contributor_bib.auth)
        assert res.status_code == 200
        assert res.content_type == 'application/vnd.api+json'
        assert len(res.json['data']) == 2

        perm_filter = '{}?filter[permission]={}'.format(url, ADMIN)
        res = app.get(perm_filter, auth=admin_contributor_bib.auth)
        assert res.status_code == 200
        assert res.content_type == 'application/vnd.api+json'
        assert len(res.json['data']) == 1
        assert res.json['data'][0]['id'] == '{}-{}'.format(preprint._id, admin_contributor_bib._id)
