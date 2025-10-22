import pytest
from datetime import timedelta
from django.utils import timezone

from osf_tests.factories import (
    UserFactory,
    NodeFactory,
    RegistrationFactory,
    PreprintFactory
)

from osf.models import (
    Node,
    Registration,
    Preprint
)

from scripts.find_spammy_content import manage_spammy_content
from tests.utils import capture_notifications


@pytest.mark.django_db
class TestFindSpammyContent:

    @pytest.fixture
    def user(self):
        return UserFactory()

    @pytest.fixture
    def user_two(self):
        return UserFactory()

    @pytest.fixture
    def kombat_node(self, user):
        return NodeFactory(title='Mortal Kombat Spam', creator=user)

    @pytest.fixture
    def node_two(self, user_two):
        return NodeFactory(title='Not Combat Spam', creator=user_two)

    @pytest.fixture
    def spam_node_but_old(self, user_two):
        node = NodeFactory(title='Kombat spam', creator=user_two)
        node.created = timezone.now() - timedelta(days=2)
        node.save()
        return node

    @pytest.fixture
    def kombat_registration(self, user):
        return RegistrationFactory(title='Mortal Kombat Spam', creator=user)

    @pytest.fixture
    def registration_two(self, user_two):
        return RegistrationFactory(title='Not Combat Spam', creator=user_two)

    @pytest.fixture
    def kombat_preprint(self, user):
        return PreprintFactory(title='Mortal Kombat Spam', creator=user)

    @pytest.fixture
    def preprint_two(self, user_two):
        return PreprintFactory(title='Not Combat Spam', creator=user_two)

    def test_get_all_node_spam(self, kombat_node, node_two):
        spam_data = manage_spammy_content('Kombat', models=[Node, ], return_csv=False)
        spam_guids = [spam['guid'] for spam in spam_data]
        assert kombat_node._id in spam_guids
        assert node_two not in spam_guids

    def test_get_all_registration_spam(self, kombat_registration, registration_two):
        spam_data = manage_spammy_content('Kombat', models=[Registration, ], return_csv=False)
        spam_guids = [spam['guid'] for spam in spam_data]
        assert kombat_registration._id in spam_guids
        assert registration_two not in spam_guids

    def test_get_all_preprint_spam(self, kombat_preprint, preprint_two):
        spam_data = manage_spammy_content('Kombat', models=[Preprint, ], return_csv=False)
        spam_guids = [spam['guid'] for spam in spam_data]
        assert kombat_preprint._id in spam_guids
        assert preprint_two not in spam_guids

    def test_get_recent_spam(self, kombat_node, spam_node_but_old):
        spam_data = manage_spammy_content('Kombat', models=[Node, ], return_csv=False)
        spam_guids = [spam['guid'] for spam in spam_data]
        assert kombat_node._id in spam_guids
        assert spam_node_but_old not in spam_guids

    def test_ban_all_node_spam(self, user, user_two, kombat_node, node_two):
        with capture_notifications():
            manage_spammy_content('Kombat', models=[Node, ], ban=True)
        user.reload()
        kombat_node.reload()
        node_two.reload()
        user_two.reload()
        assert kombat_node.is_spam
        assert not node_two.is_spam
        assert user.is_disabled
        assert not user_two.is_disabled

    def test_ban_all_preprint_spam(self, user, user_two, kombat_preprint, preprint_two):
        with capture_notifications():
            manage_spammy_content('Kombat', models=[Preprint, ], ban=True)
        kombat_preprint.reload()
        preprint_two.reload()
        user.reload()
        user_two.reload()
        assert kombat_preprint.is_spam
        assert not preprint_two.is_spam
        assert user.is_disabled
        assert not user_two.is_disabled

    def test_ban_all_registration_spam(self, user, user_two, kombat_registration, registration_two):
        with capture_notifications():
            manage_spammy_content('Kombat', models=[Registration, ], ban=True)
        user.reload()
        user_two.reload()
        kombat_registration.reload()
        registration_two.reload()
        assert kombat_registration.is_spam
        assert not registration_two.is_spam
        assert user.is_disabled
        assert not user_two.is_disabled

    def test_ban_recent_spam(self, kombat_node, spam_node_but_old, user, user_two):
        with capture_notifications():
            manage_spammy_content('Kombat', models=[Node, ], ban=True)
        kombat_node.reload()
        spam_node_but_old.reload()
        user.reload()
        user_two.reload()
        assert kombat_node.is_spam
        assert not spam_node_but_old.is_spam
        assert user.is_disabled
        assert not user_two.is_disabled
