# -*- coding: utf-8 -*-
import datetime
import mock
import os
import pytest
import time
import unittest
from django.utils import timezone

from flask import Flask
from nose.tools import *  # noqa (PEP8 asserts)
import blinker

from tests.base import OsfTestCase, DbTestCase
from osf_tests.factories import RegistrationFactory, UserFactory, fake_email

from framework.auth.utils import generate_csl_given_name
from framework.routing import Rule, json_renderer
from framework.utils import secure_filename, throttle_period_expired
from api.base.utils import waterbutler_api_url_for
from osf.utils.functional import rapply
from website.routes import process_rules, OsfWebRenderer
from website import settings
from website.util import paths
from website.util import web_url_for, api_url_for, is_json_request, conjunct, api_v2_url
from website.project import utils as project_utils
from website.profile import utils as profile_utils

try:
    import magic  # noqa
    LIBMAGIC_AVAILABLE = True
except ImportError:
    LIBMAGIC_AVAILABLE = False

HERE = os.path.dirname(os.path.abspath(__file__))

class TestTimeUtils(unittest.TestCase):
    def test_throttle_period_expired_no_timestamp(self):
        is_expired = throttle_period_expired(timestamp=None, throttle=30)
        assert_true(is_expired)

    def test_throttle_period_expired_using_datetime(self):
        timestamp = timezone.now()
        is_expired = throttle_period_expired(timestamp=(timestamp + datetime.timedelta(seconds=29)),  throttle=30)
        assert_false(is_expired)

        is_expired = throttle_period_expired(timestamp=(timestamp - datetime.timedelta(seconds=31)),  throttle=30)
        assert_true(is_expired)

    def test_throttle_period_expired_using_timestamp_in_seconds(self):
        timestamp = int(time.time())
        is_expired = throttle_period_expired(timestamp=(timestamp + 29), throttle=30)
        assert_false(is_expired)

        is_expired = throttle_period_expired(timestamp=(timestamp - 31), throttle=30)
        assert_true(is_expired)

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
        assert_equal(full_url, 'http://localhost:8000/v2/nodes/abcd3/contributors/')

        # Handles URL the same way whether or not user enters a leading slash
        full_url = api_v2_url('nodes/abcd3/contributors/',
                              base_route='http://localhost:8000/',
                              base_prefix='v2/')
        assert_equal(full_url, 'http://localhost:8000/v2/nodes/abcd3/contributors/')

    def test_api_v2_url_with_params(self):
        """Handles- and encodes- URLs with parameters (dict and kwarg) correctly"""
        full_url = api_v2_url('/nodes/abcd3/contributors/',
                              params={'filter[fullname]': 'bob'},
                              base_route='https://api.osf.io/',
                              base_prefix='v2/',
                              page_size=10)
        assert_equal(full_url, 'https://api.osf.io/v2/nodes/abcd3/contributors/?filter%5Bfullname%5D=bob&page_size=10')

    def test_api_v2_url_base_path(self):
        """Given a blank string, should return the base path (domain + port + prefix) with no extra cruft at end"""
        full_url = api_v2_url('',
                              base_route='http://localhost:8000/',
                              base_prefix='v2/')
        assert_equal(full_url, 'http://localhost:8000/v2/')

    def test_web_url_for(self):
        with self.app.test_request_context():
            assert web_url_for('dummy_view', pid='123') == '/123/'

    def test_web_url_for_guid(self):
        with self.app.test_request_context():
            # check /project/<pid>
            assert_equal('/pid123/', web_url_for('dummy_guid_project_view', pid='pid123', _guid=True))
            assert_equal('/project/pid123/', web_url_for('dummy_guid_project_view', pid='pid123', _guid=False))
            assert_equal('/project/pid123/', web_url_for('dummy_guid_project_view', pid='pid123'))
            # check /project/<pid>/node/<nid>
            assert_equal('/nid321/', web_url_for('dummy_guid_project_view', pid='pid123', nid='nid321', _guid=True))
            assert_equal(
                '/project/pid123/node/nid321/',
                web_url_for('dummy_guid_project_view', pid='pid123', nid='nid321', _guid=False))
            assert_equal(
                '/project/pid123/node/nid321/',
                web_url_for('dummy_guid_project_view', pid='pid123', nid='nid321'))
            # check /profile/<pid>
            assert_equal('/pro123/', web_url_for('dummy_guid_profile_view', pid='pro123', _guid=True))
            assert_equal('/profile/pro123/', web_url_for('dummy_guid_profile_view', pid='pro123', _guid=False))
            assert_equal('/profile/pro123/', web_url_for('dummy_guid_profile_view', pid='pro123'))

    def test_web_url_for_guid_regex_conditions(self):
        with self.app.test_request_context():
            # regex matches limit keys to a minimum of 5 alphanumeric characters.
            # check /project/<pid>
            assert_not_equal('/123/', web_url_for('dummy_guid_project_view', pid='123', _guid=True))
            assert_equal('/123456/', web_url_for('dummy_guid_project_view', pid='123456', _guid=True))
            # check /project/<pid>/node/<nid>
            assert_not_equal('/321/', web_url_for('dummy_guid_project_view', pid='123', nid='321', _guid=True))
            assert_equal('/654321/', web_url_for('dummy_guid_project_view', pid='123456', nid='654321', _guid=True))
            # check /profile/<pid>
            assert_not_equal('/123/', web_url_for('dummy_guid_profile_view', pid='123', _guid=True))
            assert_equal('/123456/', web_url_for('dummy_guid_profile_view', pid='123456', _guid=True))

    def test_web_url_for_guid_case_sensitive(self):
        with self.app.test_request_context():
            # check /project/<pid>
            assert_equal('/ABCdef/', web_url_for('dummy_guid_project_view', pid='ABCdef', _guid=True))
            # check /project/<pid>/node/<nid>
            assert_equal('/GHIjkl/', web_url_for('dummy_guid_project_view', pid='ABCdef', nid='GHIjkl', _guid=True))
            # check /profile/<pid>
            assert_equal('/MNOpqr/', web_url_for('dummy_guid_profile_view', pid='MNOpqr', _guid=True))

    def test_web_url_for_guid_invalid_unicode(self):
        with self.app.test_request_context():
            # unicode id's are not supported when encoding guid url's.
            # check /project/<pid>
            assert_not_equal('/ø∆≤µ©/', web_url_for('dummy_guid_project_view', pid='ø∆≤µ©', _guid=True))
            assert_equal(
                '/project/%C3%B8%CB%86%E2%88%86%E2%89%A4%C2%B5%CB%86/',
                web_url_for('dummy_guid_project_view', pid='øˆ∆≤µˆ', _guid=True))
            # check /project/<pid>/node/<nid>
            assert_not_equal(
                '/ø∆≤µ©/',
                web_url_for('dummy_guid_project_view', pid='ø∆≤µ©', nid='©µ≤∆ø', _guid=True))
            assert_equal(
                '/project/%C3%B8%CB%86%E2%88%86%E2%89%A4%C2%B5%CB%86/node/%C2%A9%C2%B5%E2%89%A4%E2%88%86%C3%B8/',
                web_url_for('dummy_guid_project_view', pid='øˆ∆≤µˆ', nid='©µ≤∆ø', _guid=True))
            # check /profile/<pid>
            assert_not_equal('/ø∆≤µ©/', web_url_for('dummy_guid_profile_view', pid='ø∆≤µ©', _guid=True))
            assert_equal(
                '/profile/%C3%B8%CB%86%E2%88%86%E2%89%A4%C2%B5%CB%86/',
                web_url_for('dummy_guid_profile_view', pid='øˆ∆≤µˆ', _guid=True))

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
            assert_true(is_json_request())
        with self.app.test_request_context(content_type=None):
            assert_false(is_json_request())
        with self.app.test_request_context(content_type='application/json;charset=UTF-8'):
            assert_true(is_json_request())

    def test_waterbutler_api_url_for(self):
        with self.app.test_request_context():
            url = waterbutler_api_url_for('fakeid', 'provider', '/path', base_url=settings.WATERBUTLER_URL)
        assert_in('/fakeid/', url)
        assert_in('/path', url)
        assert_in('/providers/provider/', url)
        assert_in(settings.WATERBUTLER_URL, url)

        with self.app.test_request_context():
            url = waterbutler_api_url_for('fakeid', 'provider', '/path')
        assert_in(settings.WATERBUTLER_URL, url)

    def test_waterbutler_api_url_for_internal(self):
        settings.WATERBUTLER_INTERNAL_URL = 'http://1.2.3.4:7777'
        with self.app.test_request_context():
            url = waterbutler_api_url_for('fakeid', 'provider', '/path', _internal=True, base_url=settings.WATERBUTLER_INTERNAL_URL)

        assert_not_in(settings.WATERBUTLER_URL, url)
        assert_in(settings.WATERBUTLER_INTERNAL_URL, url)
        assert_in('/fakeid/', url)
        assert_in('/path', url)
        assert_in('/providers/provider', url)


class TestFrameworkUtils(unittest.TestCase):

    def test_leading_underscores(self):
        assert_equal(
            '__init__.py',
            secure_filename('__init__.py')
        )

    def test_werkzeug_cases(self):
        """Test that Werkzeug's tests still pass for our wrapped version"""

        # Copied from Werkzeug
        # BSD licensed - original at github.com/mitsuhiko/werkzeug,
        #                /tests/test_utils.py, line 282, commit 811b438
        assert_equal(
            'My_cool_movie.mov',
            secure_filename('My cool movie.mov')
        )

        assert_equal(
            'etc_passwd',
            secure_filename('../../../etc/passwd')
        )

        assert_equal(
            'i_contain_cool_umlauts.txt',
            secure_filename(u'i contain cool \xfcml\xe4uts.txt')
        )


class TestWebpackFilter(unittest.TestCase):

    def setUp(self):
        self.asset_paths = {'assets': 'assets.07123e.js'}

    def test_resolve_asset(self):
        asset = paths.webpack_asset('assets.js', self.asset_paths, debug=False)
        assert_equal(asset, '/static/public/js/assets.07123e.js')

    def test_resolve_asset_not_found_and_not_in_debug_mode(self):
        with assert_raises(KeyError):
            paths.webpack_asset('bundle.js', self.asset_paths, debug=False)


class TestWebsiteUtils(unittest.TestCase):

    def test_conjunct(self):
        words = []
        assert_equal(conjunct(words), '')
        words = ['a']
        assert_equal(conjunct(words), 'a')
        words = ['a', 'b']
        assert_equal(conjunct(words), 'a and b')
        words = ['a', 'b', 'c']
        assert_equal(conjunct(words), 'a, b, and c')
        assert_equal(conjunct(words, conj='or'), 'a, b, or c')

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
        assert_equal(outputs['foo'], 'bar'.upper())
        assert_equal(outputs['baz']['boom'], ['kapow'.upper()])
        assert_equal(outputs['baz']['bang'], 'bam'.upper())
        assert_equal(outputs['bat'], ['man'.upper()])

        r_assert = lambda s: assert_equal(s.upper(), s)
        rapply(outputs, r_assert)

    def test_rapply_on_list(self):
        inputs = range(5)
        add_one = lambda n: n + 1
        outputs = rapply(inputs, add_one)
        for i in inputs:
            assert_equal(outputs[i], i + 1)

    def test_rapply_on_tuple(self):
        inputs = tuple(i for i in range(5))
        add_one = lambda n: n + 1
        outputs = rapply(inputs, add_one)
        for i in inputs:
            assert_equal(outputs[i], i + 1)
        assert_equal(type(outputs), tuple)

    def test_rapply_on_set(self):
        inputs = set(i for i in range(5))
        add_one = lambda n: n + 1
        outputs = rapply(inputs, add_one)
        for i in inputs:
            assert_in(i + 1, outputs)
        assert_true(isinstance(outputs, set))

    def test_rapply_on_str(self):
        input = 'bob'
        convert = lambda s: s.upper()
        outputs = rapply(input, convert)

        assert_equal('BOB', outputs)
        assert_true(isinstance(outputs, basestring))

    def test_rapply_preserves_args_and_kwargs(self):
        def zero_if_not_check(item, check, checkFn=lambda n: n):
            if check and checkFn(item):
                return item
            return 0
        inputs = range(5)
        outputs = rapply(inputs, zero_if_not_check, True, checkFn=lambda n: n % 2)
        assert_equal(outputs, [0, 1, 0, 3, 0])
        outputs = rapply(inputs, zero_if_not_check, False, checkFn=lambda n: n % 2)
        assert_equal(outputs, [0, 0, 0, 0, 0])

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
        assert_equal(len(regs), 5)
        for i in range(4):
            assert_true(regs[i].registered_date > regs[i + 1].registered_date)
        for i in range(5):
            reg = RegistrationFactory()
            reg.is_public = True
            count = count + 1
            tdiff = timezone.now() - datetime.timedelta(days=count)
            self.set_registered_date(reg, tdiff)
        regs = [r for r in project_utils.recent_public_registrations(7)]
        assert_equal(len(regs), 7)


class TestProfileUtils(DbTestCase):

    def setUp(self):
        self.user = UserFactory()

    def test_get_other_user_profile_image_default_size(self):
        profile_image = profile_utils.get_profile_image_url(self.user)
        assert_true(profile_image)

    def test_get_other_user_profile_image(self):
        profile_image = profile_utils.get_profile_image_url(self.user, size=25)
        assert_true(profile_image)


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
        assert_true(self.mock_listener.called)


class TestUserUtils(unittest.TestCase):

    def test_generate_csl_given_name_with_given_middle_suffix(self):
        given_name = 'Cause'
        middle_names = 'Awesome'
        suffix = 'Jr.'
        csl_given_name = generate_csl_given_name(
            given_name=given_name, middle_names=middle_names, suffix=suffix
        )
        assert_equal(csl_given_name, 'Cause A, Jr.')

    def test_generate_csl_given_name_with_given_middle(self):
        given_name = 'Cause'
        middle_names = 'Awesome'
        csl_given_name = generate_csl_given_name(
            given_name=given_name, middle_names=middle_names
        )
        assert_equal(csl_given_name, 'Cause A')

    def test_generate_csl_given_name_with_given_suffix(self):
        given_name = 'Cause'
        suffix = 'Jr.'
        csl_given_name = generate_csl_given_name(
            given_name=given_name, suffix=suffix
        )
        assert_equal(csl_given_name, 'Cause, Jr.')

    def test_generate_csl_given_name_with_given(self):
        given_name = 'Cause'
        csl_given_name = generate_csl_given_name(given_name)
        assert_equal(csl_given_name, 'Cause')


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
