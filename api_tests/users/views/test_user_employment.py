import pytest

from api.base.settings import API_BASE
from osf_tests.factories import EmploymentFactory
from api_tests.users.views.user_profile_test_mixin import (
    UserProfileListMixin, UserProfileDetailMixin, UserProfileCreateMixin,
    UserProfileUpdateMixin, UserProfileRelationshipMixin)


class UserEmploymentMixin:

    @pytest.fixture
    def resource_factory(self):
        return EmploymentFactory

    @pytest.fixture()
    def profile_type(self):
        return 'user-employment'

    @pytest.fixture()
    def model_name(self):
        return 'employment'


@pytest.mark.django_db
class TestUserEmploymentList(UserEmploymentMixin, UserProfileListMixin):

    @pytest.fixture
    def list_url(self, user, profile_type, model_name):
        return '/{}users/{}/{}/'.format(API_BASE, user._id, model_name)


@pytest.mark.django_db
class TestEmploymentDetail(UserEmploymentMixin, UserProfileDetailMixin):

    @pytest.fixture
    def detail_url(self, user, profile_item_one, profile_type, model_name):
        return '/{}users/{}/{}/{}/'.format(API_BASE, user._id, model_name, profile_item_one._id)


@pytest.mark.django_db
class TestUserEmploymentCreate(UserEmploymentMixin, UserProfileCreateMixin):

    @pytest.fixture
    def list_url(self, user, profile_type, model_name):
        return '/{}users/{}/{}/'.format(API_BASE, user._id, model_name)


@pytest.mark.django_db
class TestUserEmploymentUpdate(UserEmploymentMixin, UserProfileUpdateMixin):

    @pytest.fixture
    def detail_url(self, user, profile_item_one, profile_type, model_name):
        return '/{}users/{}/{}/{}/'.format(API_BASE, user._id, model_name, profile_item_one._id)


@pytest.mark.django_db
class TestUserEmploymentRelationship(UserEmploymentMixin, UserProfileRelationshipMixin):

    @pytest.fixture()
    def url(self, user, profile_type, model_name):
        return '/{}users/{}/relationships/{}/'.format(API_BASE, user._id, model_name)
