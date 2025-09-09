import pytest
from waffle.testutils import override_switch
from osf import features
from django.test import RequestFactory

from osf_tests.factories import (
    AuthUserFactory,
    RegistrationProviderFactory
)
from admin_tests.utilities import setup_view
from admin.providers.views import AddAdminOrModerator

from django.contrib.messages.storage.fallback import FallbackStorage
from osf.migrations import update_provider_auth_groups
from tests.utils import get_mailhog_messages, delete_mailhog_messages
from osf.models import NotificationType

pytestmark = pytest.mark.django_db


@pytest.mark.urls('admin.base.urls')
class TestEditModerators:

    @pytest.fixture()
    def req(self, user):
        req = RequestFactory().get('/fake_path')
        req.user = user
        return req

    @pytest.fixture()
    def provider(self):
        provider = RegistrationProviderFactory()
        update_provider_auth_groups()
        return provider

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def add_moderator_view(self, req, provider):
        view = AddAdminOrModerator()
        view = setup_view(view, req)
        view.kwargs = {'provider_id': provider.id}
        return view

    @override_switch(features.ENABLE_MAILHOG, active=True)
    def test_post_add(self, add_moderator_view, req, user, provider):
        delete_mailhog_messages()

        req.POST = {
            'csrfmiddlewaretoken': 'fake csfr',
            'add-moderators-form': [user._id],
            'moderator': ['Add Moderator']
        }

        # django.contrib.messages has a bug which effects unittests
        # more info here -> https://code.djangoproject.com/ticket/17971
        setattr(req, 'session', 'session')
        messages = FallbackStorage(req)
        setattr(req, '_messages', messages)

        res = add_moderator_view.post(req)
        assert res.status_code == 302
        assert user in provider.get_group('moderator').user_set.all()

        # try to add the same user, but another group
        req.POST = {
            'csrfmiddlewaretoken': 'fake csfr',
            'add-moderators-form': [user._id],
            'admin': ['Add Admin']
        }
        res = add_moderator_view.post(req)
        assert res.status_code == 302
        assert user in provider.get_group('moderator').user_set.all()
        assert user not in provider.get_group('admin').user_set.all()
        res = get_mailhog_messages()
        assert res['count'] == 1
        assert res['items'][0]['Content']['Headers']['To'][0] == user.username
        assert res['items'][0]['Content']['Headers']['Subject'][0] == NotificationType.objects.get(
            name=NotificationType.Type.PROVIDER_MODERATOR_ADDED
        ).subject
        delete_mailhog_messages()
