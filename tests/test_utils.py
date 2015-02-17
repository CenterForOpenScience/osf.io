# -*- coding: utf-8 -*-
import datetime
import urlparse
import os
import mock
import unittest
from flask import Flask
from nose.tools import *  # noqa (PEP8 asserts)
from modularodm import Q
from modularodm.exceptions import NoResultsFound

from framework.routing import Rule, json_renderer
from framework.utils import secure_filename
from framework.auth.core import User
from website import mails, settings
from website.routes import process_rules, OsfWebRenderer
from website.util import paths
from website.util.mimetype import get_mimetype
from website.util import web_url_for, api_url_for, is_json_request
from website.util.send_digest import send_digest, group_messages, group_digest_notifications_by_user
from website.notifications.model import DigestNotification
from tests.base import OsfTestCase
from tests.factories import DigestNotificationFactory, UserFactory, ProjectFactory

try:
    import magic
    LIBMAGIC_AVAILABLE = True
except ImportError:
    LIBMAGIC_AVAILABLE = False

HERE = os.path.dirname(os.path.abspath(__file__))


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
    def test_unknown_extension_with_no_contents_not_real_file_results_in_exception(self):
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
        asset = paths.webpack_asset('assets.js', self.asset_paths)
        assert_equal(asset, '/static/public/js/assets.07123e.js')

    def test_resolve_asset_not_found(self):
        with assert_raises(KeyError):
            paths.webpack_asset('bundle.js', self.asset_paths)


class TestSendDigest(OsfTestCase):
    def test_group_digest_notifications_by_user(self):
        user = UserFactory()
        user2 = UserFactory()
        project = ProjectFactory()
        timestamp = (datetime.datetime.utcnow() - datetime.timedelta(hours=1)).replace(microsecond=0)
        d = DigestNotificationFactory(
            user_id=user._id,
            timestamp=timestamp,
            message='Hello',
            node_lineage=[project._id]
        )
        d.save()
        d2 = DigestNotificationFactory(
            user_id=user2._id,
            timestamp=timestamp,
            message='Hello',
            node_lineage=[project._id]
        )
        d2.save()
        user_groups = group_digest_notifications_by_user()
        info = [{
                u'message': {
                    u'message': u'Hello',
                    u'timestamp': timestamp,
                },
                u'node_lineage': [unicode(project._id)]
                }]
        expected = [{
                    u'user_id': user._id,
                    u'info': info
                    },
                    {
                    u'user_id': user2._id,
                    u'info': info
                    }]
        assert_equal(len(user_groups), 2)
        assert_equal(user_groups, expected)

    @unittest.skipIf(settings.USE_CELERY, 'Digest emails must be sent synchronously for this test')
    @mock.patch('website.mails.send_mail')
    def test_send_digest_called_with_correct_args(self, mock_send_mail):
        d = DigestNotificationFactory(
            user_id=UserFactory()._id,
            timestamp=datetime.datetime.utcnow(),
            message='Hello',
            node_lineage=[ProjectFactory()._id]
        )
        d.save()
        user_groups = group_digest_notifications_by_user()
        send_digest(user_groups)
        assert_true(mock_send_mail.called)

        user = User.load(user_groups[2]['user_id'])
        mock_send_mail.assert_called_with(
            to_addr=user.username,
            mail=mails.DIGEST,
            name=user.fullname,
            message=group_messages(user_groups[2]['info']),
            url=urlparse.urljoin(settings.DOMAIN, web_url_for('user_notifications'))
        )

    @unittest.skipIf(settings.USE_CELERY, 'Digest emails must be sent synchronously for this test')
    def test_send_digest_deletes_sent_digest_notifications(self):
        d = DigestNotificationFactory(
            user_id=UserFactory()._id,
            timestamp=datetime.datetime.utcnow(),
            message='Hello',
            node_lineage=[ProjectFactory()._id]
        )
        id = d._id
        user_groups = group_digest_notifications_by_user()
        send_digest(user_groups)
        with assert_raises(NoResultsFound):
            DigestNotification.find_one(Q('_id', 'eq', id))