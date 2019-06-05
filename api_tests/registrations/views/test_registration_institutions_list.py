import pytest

from osf_tests.factories import RegistrationFactory, AuthUserFactory
from api_tests.nodes.views.test_node_institutions_list import TestNodeInstitutionList

@pytest.fixture()
def user():
    return AuthUserFactory()

@pytest.fixture()
def user_two():
    return AuthUserFactory()


@pytest.mark.django_db
class TestRegistrationInstitutionList(TestNodeInstitutionList):

    @pytest.fixture()
    def node_one(self, institution):
        # Fixture override for TestNodeInstitutionList
        node_one = RegistrationFactory(is_public=True)
        node_one.affiliated_institutions.add(institution)
        node_one.save()
        return node_one

    @pytest.fixture()
    def node_two(self, user):
        # Fixture override for TestNodeInstitutionList
        return RegistrationFactory(creator=user)
