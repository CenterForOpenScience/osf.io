import pytest

from api.base.settings import API_BASE
from osf_tests.factories import EducationFactory
from api_tests.users.views.user_profile_test_mixin import (
    UserProfileListMixin, UserProfileDetailMixin, UserProfileCreateMixin,
    UserProfileUpdateMixin, UserProfileRelationshipMixin)


class UserEducationMixin:

    @pytest.fixture
    def resource_factory(self):
        return EducationFactory

    @pytest.fixture()
    def profile_type(self):
        return 'user-education'

    @pytest.fixture()
    def model_name(self):
        return 'education'


@pytest.mark.django_db
class TestUserEducationList(UserEducationMixin, UserProfileListMixin):

    @pytest.fixture
    def list_url(self, user, model_name):
        return '/{}users/{}/{}/'.format(API_BASE, user._id, model_name)


@pytest.mark.django_db
class TestEducationDetail(UserEducationMixin, UserProfileDetailMixin):

    @pytest.fixture
    def detail_url(self, user, profile_item_one, model_name):
        return '/{}users/{}/{}/{}/'.format(API_BASE, user._id, model_name, profile_item_one._id)


@pytest.mark.django_db
class TestUserEducationCreate(UserEducationMixin, UserProfileCreateMixin):

    @pytest.fixture
    def list_url(self, user, model_name):
        return '/{}users/{}/{}/'.format(API_BASE, user._id, model_name)


@pytest.mark.django_db
class TestUserEducationUpdate(UserEducationMixin, UserProfileUpdateMixin):

    @pytest.fixture
    def detail_url(self, user, profile_item_one, model_name):
        return '/{}users/{}/{}/{}/'.format(API_BASE, user._id, model_name, profile_item_one._id)


@pytest.mark.django_db
class TestUserEducationRelationship(UserEducationMixin, UserProfileRelationshipMixin):

    @pytest.fixture()
    def url(self, user, model_name):
        return '/{}users/{}/relationships/{}/'.format(API_BASE, user._id, model_name)
