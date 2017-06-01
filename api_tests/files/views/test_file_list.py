from framework.auth.core import Auth

import pytest

from api.base.settings.defaults import API_BASE
from api_tests import utils as api_utils
from tests.base import ApiTestCase
from osf_tests.factories import (
    ProjectFactory,
    UserFactory,
    AuthUserFactory,
)

@pytest.fixture()
def user():
    return AuthUserFactory()

@pytest.mark.django_db
class TestNodeFileList:

    @pytest.fixture()
    def node(self, user):
        return ProjectFactory(creator=user)

    @pytest.fixture()
    def file(self, user, node):
        return api_utils.create_test_file(
            node, user, filename='file1')

    @pytest.fixture()
    def deleted_file(self, user, node):
        deleted_file = api_utils.create_test_file(
            node, user, filename='file2')
        deleted_file.delete(user=user, save=True)
        return deleted_file

    def test_does_not_return_trashed_files(self, app, user, node, file, deleted_file):
        res = app.get(
            '/{}nodes/{}/files/osfstorage/'.format(API_BASE, node._id),
            auth=user.auth
        )
        data = res.json.get('data')
        assert len(data) == 1

@pytest.mark.django_db
class TestFileFiltering:

    @pytest.fixture()
    def node(self, user):
        return ProjectFactory(creator=user)

    @pytest.fixture()
    def file1(self, user, node):
        return api_utils.create_test_file(
            node, user, filename='file1')

    @pytest.fixture()
    def file2(self, user, node):
        return api_utils.create_test_file(
            node, user, filename='file2')

    @pytest.fixture()
    def file3(self, user, node):
        return api_utils.create_test_file(
            node, user, filename='file3')

    @pytest.fixture()
    def file4(self, user, node):
        return api_utils.create_test_file(
            node, user, filename='file4')

    def test_get_all_files(self, app, user, node, file1, file2, file3, file4):
        res = app.get(
            '/{}nodes/{}/files/osfstorage/'.format(API_BASE, node._id),
            auth=user.auth
        )
        data = res.json.get('data')
        assert len(data) == 4

    def test_filter_on_single_tag(self, app, user, node, file1, file2, file3, file4):
        file1.add_tag('new', Auth(user))
        file2.add_tag('new', Auth(user))
        file3.add_tag('news', Auth(user))

        # test_filter_on_tag
        res = app.get(
            '/{}nodes/{}/files/osfstorage/?filter[tags]=new'.format(
                API_BASE, node._id
            ),
            auth=user.auth
        )
        data = res.json.get('data')
        assert len(data) == 2
        names = [f['attributes']['name'] for f in data]
        assert 'file1' in names
        assert 'file2' in names

        # test_filtering_tags_exact
        res = app.get(
            '/{}nodes/{}/files/osfstorage/?filter[tags]=news'.format(
                API_BASE, node._id
            ),
            auth=user.auth
        )
        assert len(res.json.get('data')) == 1

        # test_filtering_tags_capitalized_query
        res = app.get(
            '/{}nodes/{}/files/osfstorage/?filter[tags]=NEWS'.format(
                API_BASE, node._id
            ),
            auth=user.auth
        )
        assert len(res.json.get('data')) == 1

        # test_filtering_tags_capitalized_tag
        file4.add_tag('CAT', Auth(user))
        res = app.get(
            '/{}nodes/{}/files/osfstorage/?filter[tags]=cat'.format(
                API_BASE, node._id
            ),
            auth=user.auth
        )
        assert len(res.json.get('data')) == 1

    def test_filtering_on_multiple_tags(self, app, user, node, file1, file2, file3, file4):
        # test_filtering_on_multiple_tags_one_match
        file1.add_tag('cat', Auth(user))

        res = app.get(
            '/{}nodes/{}/files/osfstorage/?filter[tags]=cat&filter[tags]=sand'.format(
                API_BASE, node._id
            ),
            auth=user.auth
        )
        assert len(res.json.get('data')) == 0

        # test_filtering_on_multiple_tags_both_match
        file1.add_tag('sand', Auth(user))
        res = app.get(
            '/{}nodes/{}/files/osfstorage/?filter[tags]=cat&filter[tags]=sand'.format(
                API_BASE, node._id
            ),
            auth=user.auth
        )
        assert len(res.json.get('data')) == 1

    def test_filtering_by_tags_returns_distinct(self, app, user, node, file1, file2, file3, file4):
        # regression test for returning multiple of the same file
        file1.add_tag('cat', Auth(user))
        file1.add_tag('cAt', Auth(user))
        file1.add_tag('caT', Auth(user))
        file1.add_tag('CAT', Auth(user))
        res = app.get(
            '/{}nodes/{}/files/osfstorage/?filter[tags]=cat'.format(
                API_BASE, node._id
            ),
            auth=user.auth
        )
        assert len(res.json.get('data')) == 1
