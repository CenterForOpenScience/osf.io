import pytest

from api.base.settings.defaults import API_BASE
from osf_tests.factories import (
    AuthUserFactory,
    PreprintProviderFactory,
)
from osf.utils.permissions import ADMIN

@pytest.mark.django_db
class TestUserCanReview:

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def moderator(self, provider):
        user = AuthUserFactory()
        provider.add_to_group(user, ADMIN)
        return user

    @pytest.fixture()
    def provider(self):
        return PreprintProviderFactory(name='Sockarxiv')

    @pytest.fixture()
    def url(self):
        return '/{}users/me/?fields[users]=can_view_reviews'.format(API_BASE)

    def test_can_review(self, app, url, user, moderator, provider):
        res = app.get(url, auth=moderator.auth)
        assert res.json['data']['attributes']['can_view_reviews']

        res = app.get(url, auth=user.auth)
        assert not res.json['data']['attributes']['can_view_reviews']
