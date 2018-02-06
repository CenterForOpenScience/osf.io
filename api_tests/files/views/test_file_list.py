import pytest

from api.base.settings.defaults import API_BASE
from api_tests import utils as api_utils
from framework.auth.core import Auth
from osf_tests.factories import (
    ProjectFactory,
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
            node, user, filename='file_one')

    @pytest.fixture()
    def deleted_file(self, user, node):
        deleted_file = api_utils.create_test_file(
            node, user, filename='file_two')
        deleted_file.delete(user=user, save=True)
        return deleted_file

    def test_does_not_return_trashed_files(
            self, app, user, node, file, deleted_file):
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
    def file_one(self, user, node):
        return api_utils.create_test_file(
            node, user, filename='file_one')

    @pytest.fixture()
    def file_two(self, user, node):
        return api_utils.create_test_file(
            node, user, filename='file_two')

    @pytest.fixture()
    def file_three(self, user, node):
        return api_utils.create_test_file(
            node, user, filename='file_three')

    @pytest.fixture()
    def file_four(self, user, node):
        return api_utils.create_test_file(
            node, user, filename='file_four')

    def test_get_all_files(
            self, app, user, node, file_one, file_two,
            file_three, file_four
    ):
        res = app.get(
            '/{}nodes/{}/files/osfstorage/'.format(API_BASE, node._id),
            auth=user.auth
        )
        data = res.json.get('data')
        assert len(data) == 4

    def test_filter_on_single_tag(
            self, app, user, node,
            file_one, file_two,
            file_three, file_four
    ):
        file_one.add_tag('new', Auth(user))
        file_two.add_tag('new', Auth(user))
        file_three.add_tag('news', Auth(user))

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
        assert 'file_one' in names
        assert 'file_two' in names

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
        file_four.add_tag('CAT', Auth(user))
        res = app.get(
            '/{}nodes/{}/files/osfstorage/?filter[tags]=cat'.format(
                API_BASE, node._id
            ),
            auth=user.auth
        )
        assert len(res.json.get('data')) == 1

    def test_filtering_on_multiple_tags(
            self, app, user, node, file_one
    ):
        # test_filtering_on_multiple_tags_one_match
        file_one.add_tag('cat', Auth(user))

        res = app.get(
            '/{}nodes/{}/files/osfstorage/?filter[tags]=cat&filter[tags]=sand'.format(
                API_BASE, node._id), auth=user.auth)
        assert len(res.json.get('data')) == 0

        # test_filtering_on_multiple_tags_both_match
        file_one.add_tag('sand', Auth(user))
        res = app.get(
            '/{}nodes/{}/files/osfstorage/?filter[tags]=cat&filter[tags]=sand'.format(
                API_BASE, node._id), auth=user.auth)
        assert len(res.json.get('data')) == 1

    def test_filtering_by_tags_returns_distinct(
            self, app, user, node, file_one
    ):
        # regression test for returning multiple of the same file
        file_one.add_tag('cat', Auth(user))
        file_one.add_tag('cAt', Auth(user))
        file_one.add_tag('caT', Auth(user))
        file_one.add_tag('CAT', Auth(user))
        res = app.get(
            '/{}nodes/{}/files/osfstorage/?filter[tags]=cat'.format(
                API_BASE, node._id
            ),
            auth=user.auth
        )
        assert len(res.json.get('data')) == 1
