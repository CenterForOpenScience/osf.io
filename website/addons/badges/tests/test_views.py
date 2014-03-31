import mock
import random
import string
from nose.tools import *
import website.app
from webtest_plus import TestApp
from framework.auth.decorators import Auth

from website.addons.base.testing import AddonTestCase
from website.addons.badges.model import Badge

from tests.base import URLLookup
from utils import create_mock_badger, create_badge_dict, get_garbage

app = website.app.init_app(
            routes=True, set_backends=False, settings_module='website.settings',
        )

lookup = URLLookup(app)


class TestBadgesViews(AddonTestCase):

    ADDON_SHORT_NAME = 'badges'

    def setUp(self):

        super(TestBadgesViews, self).setUp()

    def set_node_settings(self, settings):
        return settings

    def set_user_settings(self, settings):
        return create_mock_badger(settings)

    def create_app(self):
        return TestApp(app)

    @mock.patch('website.addons.badges.model.badges.deal_with_image')
    def test_create_badge(self, img_proc):
        assert_true(self.user_settings.can_issue)
        img_proc.return_value = 'temp.png'
        badge = create_badge_dict()
        ret = self.app.post_json(lookup('api', 'create_badge'), badge, auth=self.user.auth)
        self.user_settings.reload()
        assert_equals(ret.status_int, 200)
        assert_equals(ret.content_type, 'application/json')
        assert_true(ret.json['badgeid'] in self.user_settings.badges)

    @mock.patch('website.addons.badges.model.badges.deal_with_image')
    def test_create_badge_no_data(self, img_proc):
        assert_true(self.user_settings.can_issue)
        url = lookup('api', 'create_badge')
        badge = {}
        ret = self.app.post_json(url, badge, auth=self.user.auth, expect_errors=True)
        assert_equals(ret.status_int, 400)

    @mock.patch('website.addons.badges.model.badges.deal_with_image')
    def test_create_badge_some_data(self, img_proc):
        img_proc.return_value = 'temp.png'
        assert_true(self.user_settings.can_issue)
        url = lookup('api', 'create_badge')
        badge = {
            'badgeName': ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(4)),
            'description': 'Just doesn\'t '.join(random.choice(string.ascii_letters + string.digits) for _ in range(6))
        }
        ret = self.app.post_json(url, badge, auth=self.user.auth, expect_errors=True)
        assert_equals(ret.status_int, 400)

    @mock.patch('website.addons.badges.model.badges.deal_with_image')
    def test_create_badge_empty_data(self, img_proc):
        img_proc.return_value = 'temp.png'
        assert_true(self.user_settings.can_issue)
        url = lookup('api', 'create_badge')
        badge = create_badge_dict()
        badge['imageurl'] = ''
        ret = self.app.post_json(url, badge, auth=self.user.auth, expect_errors=True)
        assert_equals(ret.status_int, 400)

    @mock.patch('website.addons.badges.model.badges.deal_with_image')
    def test_create_badge_cant_issue(self, img_proc):
        img_proc.return_value = 'temp.png'
        self.user.is_organization = False
        self.user.save()
        self.user.reload()
        assert_false(self.user_settings.can_award)
        assert_false(self.user_settings.can_issue)
        url = lookup('api', 'create_badge')
        badge = create_badge_dict()
        ret = self.app.post_json(url, badge, auth=self.user.auth, expect_errors=True)
        assert_equals(ret.status_int, 403)

    def test_award_badge(self):
        badgeid = self.user_settings.badges[0]._id
        initnum = len(self.project.badgeassertion__awarded)
        assert_true(self.user_settings.can_award)
        assert_true(self.user_settings.can_issue)
        url = lookup('api', 'award_badge', pid=self.project._id)
        ret = self.app.post_json(url, {'badgeid': badgeid}, auth=self.user.auth)
        self.project.reload()
        assert_equals(ret.status_int, 200)
        assert_equals(initnum + 1, len(self.project.badgeassertion__awarded))

    def test_award_badge_bad_badge_id(self):
        badgeid = 'badid67'
        assert_true(self.user_settings.can_award)
        assert_true(self.user_settings.can_issue)
        url = lookup('api', 'award_badge', pid=self.project._id)
        ret = self.app.post_json(url, {'badgeid': badgeid}, auth=self.user.auth, expect_errors=True)
        assert_equals(ret.status_int, 400)

    def test_award_badge_empty_badge_id(self):
        assert_true(self.user_settings.can_award)
        assert_true(self.user_settings.can_issue)
        url = lookup('api', 'award_badge', pid=self.project._id)
        ret = self.app.post_json(url, {'badgeid': ''}, auth=self.user.auth, expect_errors=True)
        assert_equals(ret.status_int, 400)

    def test_award_badge_no_badge_id(self):
        assert_true(self.user_settings.can_award)
        assert_true(self.user_settings.can_issue)
        url = lookup('api', 'award_badge', pid=self.project._id)
        ret = self.app.post_json(url, {}, auth=self.user.auth, expect_errors=True)
        assert_equals(ret.status_int, 400)

    @mock.patch('website.addons.badges.model.badges.deal_with_image')
    def test_badge_html(self, img_proc):
        assert_true(self.user_settings.can_issue)
        img_proc.return_value = 'temp.png'
        badge = {
            'badgeName': get_garbage(),
            'description': get_garbage(),
            'imageurl': get_garbage(),
            'criteria': get_garbage()
        }
        ret = self.app.post_json(lookup('api', 'create_badge'), badge, auth=self.user.auth)
        self.user_settings.reload()
        assert_equals(ret.status_int, 200)
        assert_equals(ret.content_type, 'application/json')
        assert_true(ret.json['badgeid'] in self.user_settings.badges)
        bstr = str(self.user_settings.badges[0].to_openbadge())
        assert_false('>' in bstr)
        assert_false('<' in bstr)

    def test_issuer_html(self):
        pass
