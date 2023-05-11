from datetime import timedelta
from importlib import import_module

from django.conf import settings as django_conf_settings
from django.contrib.sessions.models import Session
from django.db import IntegrityError
from django.utils import timezone
from unittest import mock
import itsdangerous
import pytest

from framework.sessions import set_current_session, get_session_from_cookie_flask, get_session
from osf.management.commands.clear_expired_sessions import clear_expired_sessions
from osf_tests.factories import AuthUserFactory
from osf.exceptions import InvalidCookieOrSessionError
from osf.models import UserSessionMap
from tests.base import fake, AppTestCase
from website import settings as osf_settings

SessionStore = import_module(django_conf_settings.SESSION_ENGINE).SessionStore
SESSION_ENGINE_DB = 'django.contrib.sessions.backends.db'
SKIP_NON_DB_BACKEND_TESTS = django_conf_settings.SESSION_ENGINE != SESSION_ENGINE_DB


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
@pytest.mark.django_db
class TestDjangoSessionStore:

    def test_construct_without_session_key(self):
        """Constructing a SessionStore() object neither generates a session_key nor save the session.
        """
        user_session = SessionStore()
        assert user_session.session_key is None

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

    def test_construct_with_fake_session_key(self, fake_session_key):
        """Constructing a SessionStore() object with a non-existing key assigns that key to the session.
        However, it doesn't save the session.
        """
        assert not SessionStore().exists(session_key=fake_session_key)
        user_session = SessionStore(session_key=fake_session_key)
        assert user_session.session_key == fake_session_key
        assert not SessionStore().exists(session_key=fake_session_key)

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

    def test_access_with_session_key(self, auth_user_session):
        assert SessionStore().exists(session_key=auth_user_session.session_key)
        user_session = SessionStore(session_key=auth_user_session.session_key)
        assert user_session.session_key == auth_user_session.session_key

    def test_update_and_save(self, auth_user_alt, auth_user_session_alt):
        auth_user_session_alt['customized_field'] = auth_user_alt._id
        auth_user_session_alt.save()
        user_session = SessionStore(session_key=auth_user_session_alt.session_key)
        assert user_session['customized_field'] == auth_user_alt._id

    @pytest.mark.skipif(SKIP_NON_DB_BACKEND_TESTS, reason='Django Session DB Backend Required for This Test')
    def test_expired_session(self, auth_user):
        session = SessionStore()
        session['auth_user_id'] = auth_user.id
        session['auth_user_username'] = auth_user.username
        session['auth_user_fullname'] = auth_user.fullname
        session.create()
        assert SessionStore().exists(session_key=session.session_key)
        from django.contrib.sessions.models import Session
        db_object = Session.objects.get(session_key=session.session_key)
        db_object.expire_date = timezone.now()
        db_object.save()
        # SessionStore().exists() does not check expiration
        assert SessionStore().exists(session_key=session.session_key)
        # However, when using an expired session_key, SessionStore() doesn't retrieve the session data
        dupe_session = SessionStore(session_key=session.session_key)
        assert dupe_session
        assert dupe_session.session_key == session.session_key
        assert dupe_session.get('auth_user_id', None) is None
        assert dupe_session.get('auth_user_username', None) is None
        assert dupe_session.get('auth_user_fullname', None) is None


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
    def test_clear_expired_sessions_remove_expired_user_session_maps(self, auth_user_session, auth_user,
                                                                     auth_user_session_alt, auth_user_alt):
        active_map = UserSessionMap.objects.create(user=auth_user, session_key=auth_user_session.session_key)
        active_map_alt = UserSessionMap.objects.create(user=auth_user, session_key=auth_user_session_alt.session_key)
        tweaked_expire_date = timezone.now() - timedelta(seconds=5)
        expired_map = UserSessionMap.objects.create(
            user=auth_user_alt,
            session_key=auth_user_session.session_key,
            expire_date=tweaked_expire_date,
        )
        expired_map_alt = UserSessionMap.objects.create(
            user=auth_user_alt,
            session_key=auth_user_session_alt.session_key,
            expire_date=tweaked_expire_date,
        )
        before_clear = UserSessionMap.objects.count()
        assert before_clear == 4
        clear_expired_sessions()
        after_clear = UserSessionMap.objects.count()
        assert after_clear == 2
        user_session_maps = UserSessionMap.objects.all()
        assert active_map in user_session_maps
        assert active_map_alt in user_session_maps
        assert expired_map not in user_session_maps
        assert expired_map_alt not in user_session_maps

    @pytest.mark.django_db
    @pytest.mark.skipif(SKIP_NON_DB_BACKEND_TESTS, reason='Django Session DB Backend Required for This Test')
    def test_clear_expired_sessions_remove_expired_sessions(self, auth_user, auth_user_alt):
        session = SessionStore()
        session['auth_user_id'] = auth_user.id
        session.create()
        assert SessionStore().exists(session_key=session.session_key)
        from django.contrib.sessions.models import Session
        db_object = Session.objects.get(session_key=session.session_key)
        db_object.expire_date = timezone.now()
        db_object.save()
        assert SessionStore().exists(session_key=session.session_key)
        assert Session.objects.filter(session_key=session.session_key).count() == 1
        clear_expired_sessions()
        assert not SessionStore().exists(session_key=session.session_key)
        assert Session.objects.filter(session_key=session.session_key).count() == 0


# In order to use AppTestCase to access `self.context.g`, we have to use unitest instead of pytest. There is an issue
# with pytest fixtures in unit tests. Unfortunately, the solution provided in the following link doesn't work :(
#   https://pytest.org/en/latest/how-to/unittest.html
@pytest.mark.django_db
class TestSessions(AppTestCase):

    def setUp(self):
        super(TestSessions, self).setUp()
        self.context.g.current_session = None
        self.user = AuthUserFactory()
        # Authenticated Session
        session = SessionStore()
        session['auth_user_id'] = self.user._primary_key
        session['auth_user_username'] = self.user.username
        session['auth_user_fullname'] = self.user.fullname
        session['customized_field'] = '13572468'
        session.create()
        self.session = session
        self.cookie = itsdangerous.Signer(osf_settings.SECRET_KEY).sign(session.session_key)
        # Anonymous Session (used for ORCiD SSO)
        session_anonymous = SessionStore()
        session_anonymous['auth_user_external_id_provider'] = 'ORCID'
        session_anonymous['auth_user_external_id'] = fake.md5()
        session_anonymous['auth_user_fullname'] = self.user.fullname
        session_anonymous['auth_user_external_first_login'] = True
        session_anonymous['customized_field'] = '12345678'
        session_anonymous.create()
        self.session_anonymous = session_anonymous
        self.cookie_session_anonymous = itsdangerous.Signer(osf_settings.SECRET_KEY).sign(session_anonymous.session_key)
        # Invalid Session
        session_invalid = SessionStore()
        session_invalid['customized_field'] = '87654321'
        session_invalid.create()
        self.cookie_session_invalid = itsdangerous.Signer(osf_settings.SECRET_KEY).sign(session_invalid.session_key)
        # Others
        self.cookie_session_removed = itsdangerous.Signer(osf_settings.SECRET_KEY).sign(fake.md5())
        self.cookie_invalid = fake.md5()

    def tearDown(self):
        super(TestSessions, self).tearDown()

    @mock.patch('framework.sessions.get_session')
    def test_set_current_session(self, mock_get_session):
        mock_get_session.return_value = self.session
        set_current_session()
        assert self.context.g.current_session is not None
        assert self.context.g.current_session.get('auth_user_id', None) == self.user._primary_key

    def test_get_session_from_cookie_without_cookie(self):
        with pytest.raises(InvalidCookieOrSessionError):
            get_session_from_cookie_flask(None)
        with pytest.raises(InvalidCookieOrSessionError):
            get_session_from_cookie_flask('')

    def test_get_session_from_cookie_with_invalid_cookie(self):
        with pytest.raises(InvalidCookieOrSessionError):
            get_session_from_cookie_flask(self.cookie_invalid)

    def test_get_session_from_cookie_with_invalid_session(self):
        with pytest.raises(InvalidCookieOrSessionError):
            get_session_from_cookie_flask(self.cookie_session_invalid)

    def test_get_session_from_cookie_with_session_gone(self):
        with pytest.raises(InvalidCookieOrSessionError):
            get_session_from_cookie_flask(self.cookie_session_removed)

    @pytest.mark.skipif(SKIP_NON_DB_BACKEND_TESTS, reason='Django Session DB Backend Required for This Test')
    def test_get_session_from_cookie_with_session_expired(self):
        # Expired Session (yet to be cleared)
        session_expired = SessionStore()
        session_expired['auth_user_id'] = self.user._primary_key
        session_expired['auth_user_username'] = self.user.username
        session_expired['auth_user_fullname'] = self.user.fullname
        session_expired['customized_field'] = '24681357'
        session_expired.create()
        session_expired_db_object = Session.objects.get(session_key=session_expired.session_key)
        session_expired_db_object.expire_date = timezone.now()
        session_expired_db_object.save()
        cookie_session_expired = itsdangerous.Signer(osf_settings.SECRET_KEY).sign(session_expired.session_key)
        with pytest.raises(InvalidCookieOrSessionError):
            get_session_from_cookie_flask(cookie_session_expired)

    def test_get_session_from_cookie_with_authenticated_session(self):
        session = get_session_from_cookie_flask(self.cookie)
        assert session is not None
        assert session.session_key == self.session.session_key
        assert session.get('auth_user_id', None) == self.user._primary_key

    def test_get_session_from_cookie_with_anonymous_session(self):
        session = get_session_from_cookie_flask(self.cookie_session_anonymous)
        assert session is not None
        assert session.session_key == self.session_anonymous.session_key
        assert session.get('auth_user_external_first_login', False)

    @mock.patch('framework.sessions.get_session_from_cookie_flask')
    @mock.patch('flask.request.cookies.get')
    def test_get_session_with_cookie_in_request(self, mock_get, mock_get_session_from_cookie_flask):
        mock_get.return_value = self.cookie
        mock_get_session_from_cookie_flask.return_value = self.session
        session = get_session()
        assert session is not None
        assert session.session_key == self.session.session_key
        assert session.get('auth_user_id', None) == self.user._primary_key
        assert self.context.g.current_session is not None
        assert self.context.g.current_session.session_key == self.session.session_key
        assert self.context.g.current_session.get('auth_user_id', None) == self.user._primary_key

    @mock.patch('framework.sessions.get_session_from_cookie_flask')
    @mock.patch('flask.request.cookies.get')
    def test_get_session_without_cookie_in_request(self, mock_get, mock_get_session_from_cookie_flask):
        mock_get.return_value = None
        mock_get_session_from_cookie_flask.assert_not_called()
        session = get_session()
        assert session is not None
        assert session.session_key is None
        assert session.get('auth_user_id', None) is None
        assert self.context.g.current_session is not None

    @mock.patch('framework.sessions.get_session_from_cookie_flask')
    @mock.patch('flask.request.cookies.get')
    def test_get_session_with_cookie_in_request_but_ignored(self, mock_get, mock_get_session_from_cookie_flask):
        mock_get.return_value = self.cookie
        session = get_session(ignore_cookie=True)
        mock_get_session_from_cookie_flask.assert_not_called()
        assert session is not None
        assert session.session_key is None
        assert session.get('auth_user_id', None) is None
        assert self.context.g.current_session is not None

    @mock.patch('framework.sessions.get_session_from_cookie_flask')
    @mock.patch('flask.request.cookies.get')
    def test_get_session_with_valid_cookie_but_session_is_removed(self, mock_get, mock_get_session_from_cookie_flask):
        mock_get.return_value = self.cookie_session_removed
        mock_get_session_from_cookie_flask.side_effect = InvalidCookieOrSessionError()
        session = get_session()
        assert session is None
        assert self.context.g.current_session is None

    @mock.patch('framework.sessions.get_session_from_cookie_flask')
    @mock.patch('flask.request.cookies.get')
    def test_get_session_with_invalid_cookie(self, mock_get, mock_get_session_from_cookie_flask):
        mock_get.return_value = self.cookie_invalid
        mock_get_session_from_cookie_flask.side_effect = InvalidCookieOrSessionError()
        session = get_session()
        assert session is None
        assert self.context.g.current_session is None

    @pytest.mark.skip
    def test_create_session_when_session_is_invalid(self):
        pass

    @pytest.mark.skip
    def test_create_session_create_new_with_response(self):
        pass

    @pytest.mark.skip
    def test_create_session_create_new_without_response(self):
        pass

    @pytest.mark.skip
    def test_create_session_update_existing_with_response(self):
        pass

    @pytest.mark.skip
    def test_create_session_update_existing_without_response(self):
        pass

    @pytest.mark.skip
    def test_before_request(self):
        pass

    @pytest.mark.skip
    def after_request(self):
        pass


@pytest.mark.django_db
class TestSessionUtils:

    @pytest.mark.skip
    def test_remove_session(self):
        pass

    @pytest.mark.skip
    def test_remove_sessions_for_user(self):
        pass
