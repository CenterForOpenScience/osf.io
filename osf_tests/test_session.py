from datetime import timedelta
from importlib import import_module

from django.conf import settings as django_conf_settings
from django.db import IntegrityError
from django.utils import timezone

import pytest


from osf_tests.factories import AuthUserFactory
from osf.models import UserSessionMap

from tests.base import fake

SessionStore = import_module(django_conf_settings.SESSION_ENGINE).SessionStore


@pytest.fixture()
def auth_user():
    return AuthUserFactory()


@pytest.fixture()
def auth_user_alt():
    return AuthUserFactory()


@pytest.fixture()
def auth_user_session(auth_user):
    user_session = SessionStore()
    user_session['auth_user_id'] = auth_user._primary_key
    user_session['auth_user_username'] = auth_user.username
    user_session['auth_user_fullname'] = auth_user.fullname
    user_session['customized_field'] = '12345678'
    user_session.create()
    return user_session


@pytest.fixture()
def auth_user_session_alt(auth_user_alt):
    user_session = SessionStore()
    user_session['auth_user_id'] = auth_user_alt._primary_key
    user_session['auth_user_username'] = auth_user_alt.username
    user_session['auth_user_fullname'] = auth_user_alt.fullname
    user_session['customized_field'] = '87654321'
    user_session.create()
    return user_session


@pytest.fixture()
def fake_session_key():
    return fake.md5()


# Although we only use Django SessionStore, we rely on expected behavior of SessionStore. When we
# upgrade Django in the future, tests in the following class should pass. If not, we must revisit
# how we understand and use SessionStore. Django's documentation is not great, we learned about
# the true nature of SessionStore only after delving into the source code as well as trial & error.
class TestDjangoSessionStore:

    @pytest.mark.django_db
    def test_construct_without_session_key(self):
        """Constructing a SessionStore() object neither generates a session_key nor save the session.
        """
        user_session = SessionStore()
        assert user_session.session_key is None

    @pytest.mark.django_db
    def test_create_without_session_key(self, auth_user):
        """Calling ``.create()`` on a SessionStore() object both generates the session key and saves the session.
        """
        user_session = SessionStore()
        user_session['auth_user_id'] = auth_user._primary_key
        user_session.create()
        assert user_session.session_key is not None
        assert SessionStore().exists(session_key=user_session.session_key)
        dupe_session = SessionStore(session_key=user_session.session_key)
        assert dupe_session['auth_user_id'] == auth_user._primary_key

    @pytest.mark.django_db
    def test_construct_with_fake_session_key(self, fake_session_key):
        """Constructing a SessionStore() object with a non-existing key assigns that key to the session.
        However, it doesn't save the session.
        """
        assert not SessionStore().exists(session_key=fake_session_key)
        user_session = SessionStore(session_key=fake_session_key)
        assert user_session.session_key == fake_session_key
        assert not SessionStore().exists(session_key=fake_session_key)

    @pytest.mark.django_db
    def test_create_with_fake_session_key(self, auth_user, fake_session_key):
        """Calling ``.create()`` on a SessionStore() object with a non-existing key saves the session.
        However, it ignores the provided key and generates a new random one.
        """
        assert not SessionStore().exists(session_key=fake_session_key)
        user_session = SessionStore(session_key=fake_session_key)
        user_session['auth_user_id'] = auth_user._primary_key
        user_session.create()
        assert not SessionStore().exists(session_key=fake_session_key)
        assert user_session.session_key != fake_session_key
        assert user_session['auth_user_id'] == auth_user._primary_key

    @pytest.mark.django_db
    def test_create_with_existing_session_key(self, auth_user_session):
        """Calling ``.create()`` on a SessionStore() object with an existing key creates a new session
        object. It has a different session key, has the same session data and is saved.
        """
        old_session_key = auth_user_session.session_key
        old_auth_user_id = auth_user_session['auth_user_id']
        user_session = SessionStore(session_key=old_session_key)
        assert user_session.session_key == old_session_key
        assert user_session['auth_user_id'] == old_auth_user_id
        user_session.create()
        assert user_session.session_key != old_session_key
        assert user_session['auth_user_id'] == old_auth_user_id
        assert SessionStore().exists(session_key=old_session_key)
        assert SessionStore().exists(session_key=user_session.session_key)

    @pytest.mark.django_db
    def test_access_with_session_key(self, auth_user_session):
        assert SessionStore().exists(session_key=auth_user_session.session_key)
        user_session = SessionStore(session_key=auth_user_session.session_key)
        assert user_session.session_key == auth_user_session.session_key

    @pytest.mark.django_db
    def test_update_and_save(self, auth_user_alt, auth_user_session_alt):
        auth_user_session_alt['customized_field'] = auth_user_alt._id
        auth_user_session_alt.save()
        user_session = SessionStore(session_key=auth_user_session_alt.session_key)
        assert user_session['customized_field'] == auth_user_alt._id


class TestUserSessionMap:

    @pytest.mark.django_db
    def test_fields(self, auth_user_session, auth_user):
        user_session_map = UserSessionMap.objects.create(
            user=auth_user,
            session_key=auth_user_session.session_key
        )
        assert user_session_map.user == auth_user
        assert user_session_map.session_key == auth_user_session.session_key
        assert user_session_map.expire_date

    @pytest.mark.django_db
    def test_expire_date_auto_set_on_create(self, auth_user_session, auth_user):
        baseline = timezone.now() + timedelta(seconds=django_conf_settings.SESSION_COOKIE_AGE)
        user_session_map = UserSessionMap.objects.create(
            user=auth_user,
            session_key=auth_user_session.session_key,
        )
        assert user_session_map.expire_date > baseline

    @pytest.mark.django_db
    def test_expire_date_auto_set_on_save(self, auth_user_session_alt, auth_user_alt):
        baseline = timezone.now() + timedelta(seconds=django_conf_settings.SESSION_COOKIE_AGE)
        user_session_map = UserSessionMap(user=auth_user_alt, session_key=auth_user_session_alt.session_key)
        user_session_map.save()
        user_session_map.reload()
        assert user_session_map.expire_date > baseline

    @pytest.mark.django_db
    def test_expire_date_manually_set_on_create(self, auth_user_session, auth_user):
        manual_expire_date = timezone.now() + timedelta(seconds=django_conf_settings.SESSION_COOKIE_AGE)
        user_session_map = UserSessionMap.objects.create(
            user=auth_user,
            session_key=auth_user_session.session_key,
            expire_date=manual_expire_date,
        )
        assert user_session_map.expire_date == manual_expire_date

    @pytest.mark.django_db
    def test_expire_date_manually_set_on_save(self, auth_user_session_alt, auth_user_alt):
        manual_expire_date = timezone.now() + timedelta(seconds=django_conf_settings.SESSION_COOKIE_AGE)
        user_session_map = UserSessionMap(
            user=auth_user_alt,
            session_key=auth_user_session_alt.session_key,
            expire_date=manual_expire_date,
        )
        user_session_map.save()
        assert user_session_map.expire_date == manual_expire_date
        updated_expire_date = timezone.now() + timedelta(seconds=django_conf_settings.SESSION_COOKIE_AGE)
        user_session_map.expire_date = updated_expire_date
        user_session_map.save()
        assert user_session_map.expire_date == updated_expire_date

    @pytest.mark.django_db
    def test_unique_constraint(self, auth_user_session, auth_user, auth_user_session_alt, auth_user_alt):
        UserSessionMap.objects.create(user=auth_user, session_key=auth_user_session.session_key)
        duplicate = UserSessionMap(user=auth_user, session_key=auth_user_session.session_key)
        with pytest.raises(IntegrityError):
            duplicate.save()

    @pytest.mark.django_db
    def test_clear_expired_sessions_remove_expired_maps(self, auth_user_session, auth_user, auth_user_session_alt, auth_user_alt):
        pass


class TestSessions:

    @pytest.mark.django_db
    @pytest.mark.skip
    def test_add_key_to_url(self):
        pass

    @pytest.mark.django_db
    @pytest.mark.skip
    def test_prepare_private_key(self):
        pass

    @pytest.mark.django_db
    @pytest.mark.skip
    def test_set_current_session(self):
        pass

    @pytest.mark.django_db
    @pytest.mark.skip
    def test_get_session_from_cookie(self):
        pass

    @pytest.mark.django_db
    @pytest.mark.skip
    def test_get_session(self):
        pass

    @pytest.mark.django_db
    @pytest.mark.skip
    def test_create_session(self):
        pass

    @pytest.mark.django_db
    @pytest.mark.skip
    def test_before_request(self):
        pass

    @pytest.mark.django_db
    @pytest.mark.skip
    def after_request(self):
        pass


class TestSessionUtils:

    @pytest.mark.django_db
    @pytest.mark.skip
    def test_remove_session(self):
        pass

    @pytest.mark.django_db
    @pytest.mark.skip
    def test_remove_sessions_for_user(self):
        pass
