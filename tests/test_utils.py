# -*- coding: utf-8 -*-
import datetime
import mock
import os
import time
import unittest

from flask import Flask
from nose.tools import *  # noqa (PEP8 asserts)
import blinker

from tests.base import OsfTestCase
from tests.factories import RegistrationFactory

from framework.routing import Rule, json_renderer
from framework.utils import secure_filename
from website.routes import process_rules, OsfWebRenderer
from website import settings
from website import util
from website.util import paths
from website.util.mimetype import get_mimetype
from website.util import web_url_for, api_url_for, is_json_request, waterbutler_url_for, conjunct, api_v2_url
from website.project import utils as project_utils
from website.util.time import throttle_period_expired

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
        timestamp = datetime.datetime.utcnow()
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
        assert_equal(full_url, "http://localhost:8000/v2/nodes/abcd3/contributors/")

        # Handles URL the same way whether or not user enters a leading slash
        full_url = api_v2_url('nodes/abcd3/contributors/',
                              base_route='http://localhost:8000/',
                              base_prefix='v2/')
        assert_equal(full_url, "http://localhost:8000/v2/nodes/abcd3/contributors/")

    def test_api_v2_url_with_params(self):
        """Handles- and encodes- URLs with parameters (dict and kwarg) correctly"""
        full_url = api_v2_url('/nodes/abcd3/contributors/',
                              params={'filter[fullname]': 'bob'},
                              base_route='https://api.osf.io/',
                              base_prefix='v2/',
                              page_size=10)
        assert_equal(full_url, "https://api.osf.io/v2/nodes/abcd3/contributors/?filter%5Bfullname%5D=bob&page_size=10")

    def test_api_v2_url_base_path(self):
        """Given a blank string, should return the base path (domain + port + prefix) with no extra cruft at end"""
        full_url = api_v2_url('',
                              base_route='http://localhost:8000/',
                              base_prefix='v2/')
        assert_equal(full_url, "http://localhost:8000/v2/")

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

    def test_waterbutler_url_for(self):
        with self.app.test_request_context():
            url = waterbutler_url_for('upload', 'provider', 'path', mock.Mock(_id='_id'))

        assert_in('nid=_id', url)
        assert_in('/file?', url)
        assert_in('path=path', url)
        assert_in('provider=provider', url)

    def test_waterbutler_url_for_implicit_cookie(self):
        with self.app.test_request_context() as context:
            context.request.cookies = {settings.COOKIE_NAME: 'cookie'}
            url = waterbutler_url_for('upload', 'provider', 'path', mock.Mock(_id='_id'))

        assert_in('nid=_id', url)
        assert_in('/file?', url)
        assert_in('path=path', url)
        assert_in('cookie=cookie', url)
        assert_in('provider=provider', url)

    def test_waterbutler_url_for_cookie_not_required(self):
        with self.app.test_request_context():
            url = waterbutler_url_for('upload', 'provider', 'path', mock.Mock(_id='_id'))

        assert_not_in('cookie', url)

        assert_in('nid=_id', url)
        assert_in('/file?', url)
        assert_in('path=path', url)
        assert_in('provider=provider', url)


class TestGetMimeTypes(unittest.TestCase):
    def test_get_markdown_mimetype_from_filename(self):
        name = 'test.md'
        mimetype = get_mimetype(name)
        assert_equal('text/x-markdown', mimetype)

    @unittest.skipIf(not LIBMAGIC_AVAILABLE, 'Must have python-magic and libmagic installed')
    def test_unknown_extension_with_no_contents_not_real_file_results_in_exception(self):
        name = 'test.thisisnotarealextensionidonotcarwhatyousay'
        with assert_raises(IOError):
            get_mimetype(name)

    @unittest.skipIf(LIBMAGIC_AVAILABLE, 'This test only runs if python-magic and libmagic are not installed')
    def test_unknown_extension_with_no_contents_not_real_file_results_in_exception2(self):
        name = 'test.thisisnotarealextensionidonotcarwhatyousay'
        mime_type = get_mimetype(name)
        assert_equal(None, mime_type)

    @unittest.skipIf(not LIBMAGIC_AVAILABLE, 'Must have python-magic and libmagic installed')
    def test_unknown_extension_with_real_file_results_in_python_mimetype(self):
        name = 'test_views.notarealfileextension'
        maybe_python_file = os.path.join(HERE, 'test_files', name)
        mimetype = get_mimetype(maybe_python_file)
        assert_equal('text/x-python', mimetype)

    @unittest.skipIf(not LIBMAGIC_AVAILABLE, 'Must have python-magic and libmagic installed')
    def test_unknown_extension_with_python_contents_results_in_python_mimetype(self):
        name = 'test.thisisnotarealextensionidonotcarwhatyousay'
        python_file = os.path.join(HERE, 'test_utils.py')
        with open(python_file, 'r') as the_file:
            content = the_file.read()
        mimetype = get_mimetype(name, content)
        assert_equal('text/x-python', mimetype)


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
        outputs = util.rapply(inputs, str.upper)
        assert_equal(outputs['foo'], 'bar'.upper())
        assert_equal(outputs['baz']['boom'], ['kapow'.upper()])
        assert_equal(outputs['baz']['bang'], 'bam'.upper())
        assert_equal(outputs['bat'], ['man'.upper()])

        r_assert = lambda s: assert_equal(s.upper(), s)
        util.rapply(outputs, r_assert)

    def test_rapply_on_list(self):
        inputs = range(5)
        add_one = lambda n: n + 1
        outputs = util.rapply(inputs, add_one)
        for i in inputs:
            assert_equal(outputs[i], i + 1)

    def test_rapply_on_tuple(self):
        inputs = tuple(i for i in range(5))
        add_one = lambda n: n + 1
        outputs = util.rapply(inputs, add_one)
        for i in inputs:
            assert_equal(outputs[i], i + 1)
        assert_equal(type(outputs), tuple)

    def test_rapply_on_set(self):
        inputs = set(i for i in range(5))
        add_one = lambda n: n + 1
        outputs = util.rapply(inputs, add_one)
        for i in inputs:
            assert_in(i + 1, outputs)
        assert_true(isinstance(outputs, set))

    def test_rapply_on_str(self):
        input = "bob"
        convert = lambda s: s.upper()
        outputs = util.rapply(input, convert)

        assert_equal("BOB", outputs)
        assert_true(isinstance(outputs, basestring))

    def test_rapply_preserves_args_and_kwargs(self):
        def zero_if_not_check(item, check, checkFn=lambda n: n):
            if check and checkFn(item):
                return item
            return 0
        inputs = range(5)
        outputs = util.rapply(inputs, zero_if_not_check, True, checkFn=lambda n: n % 2)
        assert_equal(outputs, [0, 1, 0, 3, 0])
        outputs = util.rapply(inputs, zero_if_not_check, False, checkFn=lambda n: n % 2)
        assert_equal(outputs, [0, 0, 0, 0, 0])

class TestProjectUtils(OsfTestCase):

    def set_registered_date(self, reg, date):
        reg._fields['registered_date'].__set__(
            reg,
            date,
            safe=True
        )
        reg.save()

    def test_get_recent_public_registrations(self):

        count = 0
        for i in range(5):
            reg = RegistrationFactory()
            reg.is_public = True
            count = count + 1
            tdiff = datetime.datetime.now() - datetime.timedelta(days=count)
            self.set_registered_date(reg, tdiff)
        regs = [r for r in project_utils.recent_public_registrations()]
        assert_equal(len(regs), 5)
        for i in range(4):
            assert_true(regs[i].registered_date > regs[i + 1].registered_date)
        for i in range(5):
            reg = RegistrationFactory()
            reg.is_public = True
            count = count + 1
            tdiff = datetime.datetime.now() - datetime.timedelta(days=count)
            self.set_registered_date(reg, tdiff)
        regs = [r for r in project_utils.recent_public_registrations(7)]
        assert_equal(len(regs), 7)


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

    def test_temporary_disconnect(self):
        self.signal_.connect(self.listener)
        with util.disconnected_from(self.signal_, self.listener):
            self.signal_.send()
        assert_false(self.mock_listener.called)
