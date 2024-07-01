import datetime
from unittest import mock
import os
import pytest
import time
import unittest
from django.utils import timezone
from django.dispatch import receiver


from flask import Flask
import blinker

from tests.base import OsfTestCase, DbTestCase
from osf_tests.factories import RegistrationFactory, UserFactory, fake_email
from framework.auth.signals import (
    user_account_deactivated,
    user_account_reactivated,
    user_account_merged
)

from framework.auth.utils import generate_csl_given_name
from framework.routing import Rule, json_renderer
from framework.utils import secure_filename, throttle_period_expired
from api.base.utils import waterbutler_api_url_for
from osf.utils.functional import rapply
from waffle.testutils import override_flag
from website.routes import process_rules, OsfWebRenderer
from website import settings
from website.util import paths
from website.util import web_url_for, api_url_for, is_json_request, conjunct, api_v2_url
from website.project import utils as project_utils
from website.profile import utils as profile_utils

from osf import features

from kombu import Exchange

HERE = os.path.dirname(os.path.abspath(__file__))


class TestTimeUtils(unittest.TestCase):
    def test_throttle_period_expired_no_timestamp(self):
        is_expired = throttle_period_expired(timestamp=None, throttle=30)
        assert is_expired

    def test_throttle_period_expired_using_datetime(self):
        timestamp = timezone.now()
        is_expired = throttle_period_expired(timestamp=(timestamp + datetime.timedelta(seconds=29)),  throttle=30)
        assert not is_expired

        is_expired = throttle_period_expired(timestamp=(timestamp - datetime.timedelta(seconds=31)),  throttle=30)
        assert is_expired

    def test_throttle_period_expired_using_timestamp_in_seconds(self):
        timestamp = int(time.time())
        is_expired = throttle_period_expired(timestamp=(timestamp + 29), throttle=30)
        assert not is_expired

        is_expired = throttle_period_expired(timestamp=(timestamp - 31), throttle=30)
        assert is_expired

class TestUrlForHelpers(unittest.TestCase):

    def setUp(self):
        def dummy_view():
            return {}

        def dummy_guid_project_view():
            return {}

        def dummy_guid_profile_view():
            return {}

        self.app = Flask(__name__)

        api_rule = Rule([
            '/api/v1/<pid>/',
            '/api/v1/<pid>/component/<nid>/'
        ], 'get', dummy_view, json_renderer)
        web_rule = Rule([
            '/<pid>/',
            '/<pid>/component/<nid>/'
        ], 'get', dummy_view, OsfWebRenderer)
        web_guid_project_rule = Rule([
            '/project/<pid>/',
            '/project/<pid>/node/<nid>/',
        ], 'get', dummy_guid_project_view, OsfWebRenderer)
        web_guid_profile_rule = Rule([
            '/profile/<pid>/',
        ], 'get', dummy_guid_profile_view, OsfWebRenderer)

        process_rules(self.app, [api_rule, web_rule, web_guid_project_rule, web_guid_profile_rule])

    def test_api_url_for(self):
        with self.app.test_request_context():
            assert api_url_for('dummy_view', pid='123') == '/api/v1/123/'

    def test_api_v2_url_with_port(self):
        full_url = api_v2_url('/nodes/abcd3/contributors/',
                              base_route='http://localhost:8000/',
                              base_prefix='v2/')
        assert full_url == 'http://localhost:8000/v2/nodes/abcd3/contributors/'

        # Handles URL the same way whether or not user enters a leading slash
        full_url = api_v2_url('nodes/abcd3/contributors/',
                              base_route='http://localhost:8000/',
                              base_prefix='v2/')
        assert full_url == 'http://localhost:8000/v2/nodes/abcd3/contributors/'

    def test_api_v2_url_with_params(self):
        """Handles- and encodes- URLs with parameters (dict and kwarg) correctly"""
        full_url = api_v2_url('/nodes/abcd3/contributors/',
                              params={'filter[fullname]': 'bob'},
                              base_route='https://api.osf.io/',
                              base_prefix='v2/',
                              page_size=10)
        assert full_url == 'https://api.osf.io/v2/nodes/abcd3/contributors/?filter%5Bfullname%5D=bob&page_size=10'

    def test_api_v2_url_base_path(self):
        """Given a blank string, should return the base path (domain + port + prefix) with no extra cruft at end"""
        full_url = api_v2_url('',
                              base_route='http://localhost:8000/',
                              base_prefix='v2/')
        assert full_url == 'http://localhost:8000/v2/'

    def test_web_url_for(self):
        with self.app.test_request_context():
            assert web_url_for('dummy_view', pid='123') == '/123/'

    def test_web_url_for_guid(self):
        with self.app.test_request_context():
            # check /project/<pid>
            assert '/pid123/' == web_url_for('dummy_guid_project_view', pid='pid123', _guid=True)
            assert '/project/pid123/' == web_url_for('dummy_guid_project_view', pid='pid123', _guid=False)
            assert '/project/pid123/' == web_url_for('dummy_guid_project_view', pid='pid123')
            # check /project/<pid>/node/<nid>
            assert '/nid321/' == web_url_for('dummy_guid_project_view', pid='pid123',
                                                                 nid='nid321', _guid=True)
            assert '/project/pid123/node/nid321/' == web_url_for('dummy_guid_project_view', pid='pid123',
                                                                 nid='nid321', _guid=False)
            assert '/project/pid123/node/nid321/' == web_url_for('dummy_guid_project_view',
                                                                 pid='pid123', nid='nid321')
            # check /profile/<pid>
            assert '/pro123/' == web_url_for('dummy_guid_profile_view', pid='pro123', _guid=True)
            assert '/profile/pro123/' == web_url_for('dummy_guid_profile_view', pid='pro123', _guid=False)
            assert '/profile/pro123/' == web_url_for('dummy_guid_profile_view', pid='pro123')

    def test_web_url_for_guid_regex_conditions(self):
        with self.app.test_request_context():
            # regex matches limit keys to a minimum of 5 alphanumeric characters.
            # check /project/<pid>
            assert '/123/' != web_url_for('dummy_guid_project_view', pid='123', _guid=True)
            assert '/123456/' == web_url_for('dummy_guid_project_view', pid='123456', _guid=True)
            # check /project/<pid>/node/<nid>
            assert '/321/' != web_url_for('dummy_guid_project_view', pid='123', nid='321', _guid=True)
            assert '/654321/' == web_url_for('dummy_guid_project_view', pid='123456', nid='654321', _guid=True)
            # check /profile/<pid>
            assert '/123/' != web_url_for('dummy_guid_profile_view', pid='123', _guid=True)
            assert '/123456/' == web_url_for('dummy_guid_profile_view', pid='123456', _guid=True)

    def test_web_url_for_guid_case_sensitive(self):
        with self.app.test_request_context():
            # check /project/<pid>
            assert '/ABCdef/' == web_url_for('dummy_guid_project_view', pid='ABCdef', _guid=True)
            # check /project/<pid>/node/<nid>
            assert '/GHIjkl/' == web_url_for('dummy_guid_project_view', pid='ABCdef', nid='GHIjkl', _guid=True)
            # check /profile/<pid>
            assert '/MNOpqr/' == web_url_for('dummy_guid_profile_view', pid='MNOpqr', _guid=True)

    def test_web_url_for_guid_invalid_unicode(self):
        with self.app.test_request_context():
            # unicode id's are not supported when encoding guid url's.
            # check /project/<pid>
            assert '/ø∆≤µ©/' != web_url_for('dummy_guid_project_view', pid='ø∆≤µ©', _guid=True)
            assert '/project/%C3%B8%CB%86%E2%88%86%E2%89%A4%C2%B5%CB%86/' == web_url_for(
                'dummy_guid_project_view', pid='øˆ∆≤µˆ', _guid=True)
            # check /project/<pid>/node/<nid>
            assert '/ø∆≤µ©/' != web_url_for('dummy_guid_project_view', pid='ø∆≤µ©', nid='©µ≤∆ø', _guid=True)
            assert ('/project/%C3%B8%CB%86%E2%88%86%E2%89%A4%C2%B5%CB%86/node/'
                    '%C2%A9%C2%B5%E2%89%A4%E2%88%86%C3%B8/') == web_url_for('dummy_guid_project_view',
                                                                            pid='øˆ∆≤µˆ', nid='©µ≤∆ø', _guid=True)
            # check /profile/<pid>
            assert '/ø∆≤µ©/' != web_url_for('dummy_guid_profile_view', pid='ø∆≤µ©', _guid=True)
            assert '/profile/%C3%B8%CB%86%E2%88%86%E2%89%A4%C2%B5%CB%86/' == web_url_for(''
                                                     'dummy_guid_profile_view', pid='øˆ∆≤µˆ', _guid=True)

    def test_api_url_for_with_multiple_urls(self):
        with self.app.test_request_context():
            url = api_url_for('dummy_view', pid='123', nid='abc')
            assert url == '/api/v1/123/component/abc/'

    def test_web_url_for_with_multiple_urls(self):
        with self.app.test_request_context():
            url = web_url_for('dummy_view', pid='123', nid='abc')
            assert url == '/123/component/abc/'

    def test_is_json_request(self):
        with self.app.test_request_context(content_type='application/json'):
            assert is_json_request()
        with self.app.test_request_context(content_type=None):
            assert not is_json_request()
        with self.app.test_request_context(content_type='application/json;charset=UTF-8'):
            assert is_json_request()

    def test_waterbutler_api_url_for(self):
        with self.app.test_request_context():
            url = waterbutler_api_url_for('fakeid', 'provider', '/path', base_url=settings.WATERBUTLER_URL)
        assert '/fakeid/' in url
        assert '/path' in url
        assert '/providers/provider/' in url
        assert settings.WATERBUTLER_URL in url

        with self.app.test_request_context():
            url = waterbutler_api_url_for('fakeid', 'provider', '/path')
        assert settings.WATERBUTLER_URL in url

    def test_waterbutler_api_url_for_internal(self):
        settings.WATERBUTLER_INTERNAL_URL = 'http://1.2.3.4:7777'
        with self.app.test_request_context():
            url = waterbutler_api_url_for('fakeid', 'provider', '/path', _internal=True, base_url=settings.WATERBUTLER_INTERNAL_URL)

        assert settings.WATERBUTLER_URL not in url
        assert settings.WATERBUTLER_INTERNAL_URL in url
        assert '/fakeid/' in url
        assert '/path' in url
        assert '/providers/provider' in url


class TestFrameworkUtils(unittest.TestCase):

    def test_leading_underscores(self):
        assert '__init__.py' == secure_filename('__init__.py')

    def test_werkzeug_cases(self):
        """Test that Werkzeug's tests still pass for our wrapped version"""

        # Copied from Werkzeug
        # BSD licensed - original at github.com/mitsuhiko/werkzeug,
        #                /tests/test_utils.py, line 282, commit 811b438
        assert 'My_cool_movie.mov' == secure_filename('My cool movie.mov')

        assert 'etc_passwd' == secure_filename('../../../etc/passwd')

        assert 'i_contain_cool_umlauts.txt' == secure_filename('i contain cool \xfcml\xe4uts.txt')


class TestWebpackFilter(unittest.TestCase):

    def setUp(self):
        self.asset_paths = {'assets': {'js': 'assets.07123e.js'}}

    def test_resolve_asset(self):
        asset = paths.webpack_asset('assets.js', self.asset_paths, debug=False)
        assert asset == '/static/public/js/assets.07123e.js'

    def test_resolve_asset_not_found_and_not_in_debug_mode(self):
        with pytest.raises(KeyError):
            paths.webpack_asset('bundle.js', self.asset_paths, debug=False)


def r_assert(s):
    assert s.upper() == s, f'{s.upper()} is not equal to {s}'


class TestWebsiteUtils(unittest.TestCase):

    def test_conjunct(self):
        words = []
        assert conjunct(words) == ''
        words = ['a']
        assert conjunct(words) == 'a'
        words = ['a', 'b']
        assert conjunct(words) == 'a and b'
        words = ['a', 'b', 'c']
        assert conjunct(words) == 'a, b, and c'
        assert conjunct(words, conj='or') == 'a, b, or c'

    def test_rapply(self):
        inputs = {
            'foo': 'bar',
            'baz': {
                'boom': ['kapow'],
                'bang': 'bam'
            },
            'bat': ['man']
        }
        outputs = rapply(inputs, str.upper)
        assert outputs['foo'] == 'bar'.upper()
        assert outputs['baz']['boom'] == ['kapow'.upper()]
        assert outputs['baz']['bang'] == 'bam'.upper()
        assert outputs['bat'] == ['man'.upper()]

        rapply(outputs, r_assert)

    def test_rapply_on_list(self):
        inputs = list(range(5))
        add_one = lambda n: n + 1
        outputs = rapply(inputs, add_one)
        for i in inputs:
            assert outputs[i] == i + 1

    def test_rapply_on_tuple(self):
        inputs = tuple(i for i in range(5))
        add_one = lambda n: n + 1
        outputs = rapply(inputs, add_one)
        for i in inputs:
            assert outputs[i] == i + 1
        assert type(outputs) == tuple

    def test_rapply_on_set(self):
        inputs = {i for i in range(5)}
        add_one = lambda n: n + 1
        outputs = rapply(inputs, add_one)
        for i in inputs:
            assert i + 1 in outputs
        assert isinstance(outputs, set)

    def test_rapply_on_str(self):
        input = 'bob'
        convert = lambda s: s.upper()
        outputs = rapply(input, convert)

        assert 'BOB' == outputs
        assert isinstance(outputs, str)

    def test_rapply_preserves_args_and_kwargs(self):
        def zero_if_not_check(item, check, checkFn=lambda n: n):
            if check and checkFn(item):
                return item
            return 0
        inputs = list(range(5))
        outputs = rapply(inputs, zero_if_not_check, True, checkFn=lambda n: n % 2)
        assert outputs == [0, 1, 0, 3, 0]
        outputs = rapply(inputs, zero_if_not_check, False, checkFn=lambda n: n % 2)
        assert outputs == [0, 0, 0, 0, 0]

class TestProjectUtils(OsfTestCase):

    def set_registered_date(self, reg, date):
        reg.registered_date = date
        reg.save()

    def test_get_recent_public_registrations(self):

        count = 0
        for i in range(5):
            reg = RegistrationFactory()
            reg.is_public = True
            count = count + 1
            tdiff = timezone.now() - datetime.timedelta(days=count)
            self.set_registered_date(reg, tdiff)
        regs = [r for r in project_utils.recent_public_registrations()]
        assert len(regs) == 5
        for i in range(4):
            assert regs[i].registered_date > regs[i + 1].registered_date
        for i in range(5):
            reg = RegistrationFactory()
            reg.is_public = True
            count = count + 1
            tdiff = timezone.now() - datetime.timedelta(days=count)
            self.set_registered_date(reg, tdiff)
        regs = [r for r in project_utils.recent_public_registrations(7)]
        assert len(regs) == 7


class TestProfileUtils(DbTestCase):

    def setUp(self):
        self.user = UserFactory()

    def test_get_other_user_profile_image_default_size(self):
        profile_image = profile_utils.get_profile_image_url(self.user)
        assert profile_image

    def test_get_other_user_profile_image(self):
        profile_image = profile_utils.get_profile_image_url(self.user, size=25)
        assert profile_image


class TestSignalUtils(unittest.TestCase):

    def setUp(self):
        self.signals = blinker.Namespace()
        self.signal_ = self.signals.signal('signal-')
        self.mock_listener = mock.MagicMock()

    def listener(self, signal):
        self.mock_listener()

    def test_signal(self):
        self.signal_.connect(self.listener)
        self.signal_.send()
        assert self.mock_listener.called


class TestUserUtils(unittest.TestCase):

    def test_generate_csl_given_name_with_given_middle_suffix(self):
        given_name = 'Cause'
        middle_names = 'Awesome'
        suffix = 'Jr.'
        csl_given_name = generate_csl_given_name(
            given_name=given_name, middle_names=middle_names, suffix=suffix
        )
        assert csl_given_name == 'Cause A, Jr.'

    def test_generate_csl_given_name_with_given_middle(self):
        given_name = 'Cause'
        middle_names = 'Awesome'
        csl_given_name = generate_csl_given_name(
            given_name=given_name, middle_names=middle_names
        )
        assert csl_given_name == 'Cause A'

    def test_generate_csl_given_name_with_given_suffix(self):
        given_name = 'Cause'
        suffix = 'Jr.'
        csl_given_name = generate_csl_given_name(
            given_name=given_name, suffix=suffix
        )
        assert csl_given_name == 'Cause, Jr.'

    def test_generate_csl_given_name_with_given(self):
        given_name = 'Cause'
        csl_given_name = generate_csl_given_name(given_name)
        assert csl_given_name == 'Cause'


@pytest.mark.django_db
class TestUserFactoryConflict:

    def test_build_create_user_time_conflict(self):
        # Test that build and create user factories do not create conflicting usernames
        # because they occured quickly
        user_email_one = fake_email()
        user_email_two = fake_email()
        assert user_email_one != user_email_two

        user_one_build = UserFactory.build()
        user_two_build = UserFactory.build()
        assert user_one_build.username != user_two_build.username

        user_one_create = UserFactory()
        user_two_create = UserFactory()
        assert user_one_create.username != user_two_create.username


@pytest.mark.django_db
class TestUserSignals:

    @pytest.fixture
    def user(self, db):
        return UserFactory()

    @pytest.fixture
    def old_user(self, db):
        return UserFactory()

    @pytest.fixture
    def deactivated_user(self, db):
        user = UserFactory()
        user.deactivate_account()
        return user

    @pytest.fixture
    def account_status_changes_exchange(self):
        return Exchange('account_status_changes')

    @mock.patch('osf.external.messages.celery_publishers.publish_deactivated_user')
    def test_user_account_deactivated_signal(self, mock_publish_deactivated_user, user):
        # Connect a mock receiver to the signal for testing
        @receiver(user_account_deactivated)
        def mock_receiver(user, **kwargs):
            return mock_publish_deactivated_user(user)

        # Trigger the signal
        user.deactivate_account()

        # Verify that the mock receiver was called
        mock_publish_deactivated_user.assert_called_once_with(user)

    @mock.patch('osf.external.messages.celery_publishers.publish_merged_user')
    def test_user_account_merged_signal(self, mock_publish_merged_user, user, old_user):
        # Connect a mock receiver to the signal for testing
        @receiver(user_account_merged)
        def mock_receiver(user, **kwargs):
            return mock_publish_merged_user(user)

        # Trigger the signal
        user.merge_user(old_user)

        # Verify that the mock receiver was called
        mock_publish_merged_user.assert_called_once_with(old_user)

    @mock.patch('osf.external.messages.celery_publishers.publish_reactivate_user')
    def test_user_account_deactivate_signal(self, mock_publish_reactivate_user, deactivated_user):
        # Connect a mock receiver to the signal for testing
        @receiver(user_account_reactivated)
        def mock_receiver(user, **kwargs):
            return mock_publish_reactivate_user(user)

        # Trigger the signal
        deactivated_user.reactivate_account()

        # Verify that the mock receiver was called
        mock_publish_reactivate_user.assert_called_once_with(deactivated_user)

    @pytest.mark.enable_account_status_messaging
    @mock.patch('osf.external.messages.celery_publishers.celery_app.producer_pool.acquire')
    def test_publish_body_on_deactivation(self, mock_publish_user_status_change, user, account_status_changes_exchange):
        with mock.patch.object(settings, 'USE_CELERY', True):
            with override_flag(features.ENABLE_GV, active=True):
                user.deactivate_account()

        mock_publish_user_status_change().__enter__().publish.assert_called_once_with(
            body={'action': 'deactivate', 'user_uri': f'http://localhost:5000/{user._id}'},
            exchange=account_status_changes_exchange,
            serializer='json',
        )

    @pytest.mark.enable_account_status_messaging
    @mock.patch('osf.external.messages.celery_publishers.celery_app.producer_pool.acquire')
    def test_publish_body_on_reactivation(
            self,
            mock_publish_user_status_change,
            deactivated_user,
            account_status_changes_exchange
    ):
        with mock.patch.object(settings, 'USE_CELERY', True):
            with override_flag(features.ENABLE_GV, active=True):
                deactivated_user.reactivate_account()

        mock_publish_user_status_change().__enter__().publish.assert_called_once_with(
            body={'action': 'reactivate', 'user_uri': f'http://localhost:5000/{deactivated_user._id}'},
            exchange=account_status_changes_exchange,
            serializer='json',
        )

    @pytest.mark.enable_account_status_messaging
    @mock.patch('osf.external.messages.celery_publishers.celery_app.producer_pool.acquire')
    def test_publish_body_on_merger(
            self,
            mock_publish_user_status_change,
            user,
            old_user,
            account_status_changes_exchange
    ):
        with mock.patch.object(settings, 'USE_CELERY', True):
            with override_flag(features.ENABLE_GV, active=True):
                user.merge_user(old_user)

        mock_publish_user_status_change().__enter__().publish.assert_called_once_with(
            body={
                'action': 'merge',
                'into_user_uri': f'http://localhost:5000/{user._id}',
                'from_user_uri': f'http://localhost:5000/{old_user._id}'
            },
            exchange=account_status_changes_exchange,
            serializer='json',
        )
