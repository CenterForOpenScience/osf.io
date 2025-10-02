import pytest

from framework.auth.core import get_user
from tests.utils import capture_notifications

from .factories import UserFactory

@pytest.mark.django_db
class TestGetUser:

    def test_get_user_by_email(self):
        user = UserFactory()
        assert get_user(email=user.username) == user
        assert get_user(email=user.username.upper()) == user

    def test_get_user_with_wrong_password_returns_false(self):
        user = UserFactory.build()
        with capture_notifications():
            user.set_password('killerqueen')
        assert bool(
            get_user(email=user.username, password='wrong')
        ) is False
