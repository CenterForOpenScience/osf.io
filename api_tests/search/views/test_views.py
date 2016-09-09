from nose.tools import *  # flake8: noqa

from api.base.settings.defaults import API_BASE

from tests.base import ApiTestCase
from tests.factories import (
    ProjectFactory,
    NodeFactory,
    UserFactory,
    RegistrationFactory,
)


class TestSearch(ApiTestCase):

    def setUp(self):
        pass

    def test_search_logged_in(self):
        pass

    def test_search_not_logged_in(self):
        pass


class TestSearchComponents(ApiTestCase):

    def setUp(self):
        pass

    def test_search_public_component_not_logged_in(self):
        pass

    def test_search_public_component_non_contributor(self):
        pass

    def test_search_public_component_contributor(self):
        pass

    def test_search_private_component_not_logged_in(self):
        pass

    def test_search_private_component_non_contributor(self):
        pass

    def test_search_private_component_contributor(self):
        pass


class TestSearchFiles(ApiTestCase):

    def setUp(self):
        pass

    def test_search_public_file_not_logged_in(self):
        pass

    def test_search_public_file_non_contributor(self):
        pass

    def test_search_public_file_contributor(self):
        pass

    def test_search_private_file_not_logged_in(self):
        pass

    def test_search_private_file_non_contributor(self):
        pass

    def test_search_private_file_contributor(self):
        pass


class TestSearchProjects(ApiTestCase):

    def setUp(self):
        pass

    def test_search_public_project_not_logged_in(self):
        pass

    def test_search_public_project_non_contributor(self):
        pass

    def test_search_public_project_contributor(self):
        pass

    def test_search_private_project_not_logged_in(self):
        pass

    def test_search_private_project_non_contributor(self):
        pass

    def test_search_private_project_contributor(self):
        pass

    def test_search_project_by_title(self):
        pass

    def test_search_project_by_description(self):
        pass

    def test_search_project_by_category(self):
        pass

    def test_search_project_by_tags(self):
        pass

    def test_search_project_by_contributor(self):
        # is this a thing?
        pass

    def test_search_project_no_results(self):
        pass

    def test_search_project_bad_query(self):
        pass

    def test_search_project_pagination(self):
        # should this be here or in serializer test?
        pass


class TestSearchRegistrations(ApiTestCase):

    def setUp(self):
        pass

    def test_search_public_registration_not_logged_in(self):
        pass

    def test_search_public_registration_non_contributor(self):
        pass

    def test_search_public_registration_contributor(self):
        pass

    def test_search_private_registration_not_logged_in(self):
        pass

    def test_search_private_registration_non_contributor(self):
        pass

    def test_search_private_registration_contributor(self):
        pass


class TestSearchUsers(ApiTestCase):

    def setUp(self):
        pass

    def test_search_users_not_logged_in(self):
        pass

    def test_search_users_logged_in(self):
        pass

    def test_search_users_read_scope(self):
        pass

    def test_search_users_non_read_scope(self):
        pass
