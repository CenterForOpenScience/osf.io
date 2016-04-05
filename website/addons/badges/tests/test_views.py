import mock
import random
import string
from nose.tools import *
import website.app
from webtest_plus import TestApp

from website.util import api_url_for, web_url_for
from website.addons.base.testing import AddonTestCase
from website.addons.badges.util import get_node_badges

from tests.factories import AuthUserFactory
from utils import create_mock_badger, create_badge_dict, get_garbage


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

    @mock.patch('website.addons.badges.model.badges.acquire_badge_image')
    def test_create_badge(self, img_proc):
        img_proc.return_value = 'temp.png'
        badge = create_badge_dict()
        ret = self.app.post_json(api_url_for('create_badge'), badge, auth=self.user.auth)
        self.user_settings.reload()
        assert_equals(ret.status_int, 201)
        assert_equals(ret.content_type, 'application/json')
        assert_true(ret.json['badgeid'] in [badge._id for badge in self.user_settings.badges])

    @mock.patch('website.addons.badges.model.badges.acquire_badge_image')
    def test_create_badge_no_data(self, img_proc):
        url = api_url_for('create_badge')
        badge = {}
        ret = self.app.post_json(url, badge, auth=self.user.auth, expect_errors=True)
        assert_equals(ret.status_int, 400)

    @mock.patch('website.addons.badges.model.badges.acquire_badge_image')
    def test_create_badge_some_data(self, img_proc):
        img_proc.return_value = 'temp.png'
        url = api_url_for('create_badge')
        badge = {
            'badgeName': ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(4)),
            'description': 'Just doesn\'t '.join(random.choice(string.ascii_letters + string.digits) for _ in range(6))
        }
        ret = self.app.post_json(url, badge, auth=self.user.auth, expect_errors=True)
        assert_equals(ret.status_int, 400)

    @mock.patch('website.addons.badges.model.badges.acquire_badge_image')
    def test_create_badge_empty_data(self, img_proc):
        img_proc.return_value = 'temp.png'
        url = api_url_for('create_badge')
        badge = create_badge_dict()
        badge['imageurl'] = ''
        ret = self.app.post_json(url, badge, auth=self.user.auth, expect_errors=True)
        assert_equals(ret.status_int, 400)

    @mock.patch('website.addons.badges.model.badges.acquire_badge_image')
    def test_create_badge_cant_issue(self, img_proc):
        img_proc.return_value = 'temp.png'
        self.user.delete_addon('badges')
        url = api_url_for('create_badge')
        badge = create_badge_dict()
        ret = self.app.post_json(url, badge, auth=self.user.auth, expect_errors=True)
        assert_equals(ret.status_int, 400)

    def test_award_badge(self):
        badgeid = self.user_settings.badges[0]._id
        initnum = get_node_badges(self.project).count()
        assert_true(self.user_settings.can_award)
        url = api_url_for('award_badge', pid=self.project._id)
        ret = self.app.post_json(url, {'badgeid': badgeid}, auth=self.user.auth)
        self.project.reload()
        assert_equals(ret.status_int, 200)
        assert_equals(initnum + 1, get_node_badges(self.project).count())

    def test_award_badge_bad_badge_id(self):
        badgeid = 'badid67'
        assert_true(self.user_settings.can_award)
        url = api_url_for('award_badge', pid=self.project._id)
        ret = self.app.post_json(url, {'badgeid': badgeid}, auth=self.user.auth, expect_errors=True)
        assert_equals(ret.status_int, 400)

    def test_award_badge_empty_badge_id(self):
        assert_true(self.user_settings.can_award)
        url = api_url_for('award_badge', pid=self.project._id)
        ret = self.app.post_json(url, {'badgeid': ''}, auth=self.user.auth, expect_errors=True)
        assert_equals(ret.status_int, 400)

    def test_award_badge_no_badge_id(self):
        assert_true(self.user_settings.can_award)
        url = api_url_for('award_badge', pid=self.project._id)
        ret = self.app.post_json(url, {}, auth=self.user.auth, expect_errors=True)
        assert_equals(ret.status_int, 400)

    @mock.patch('website.addons.badges.model.badges.acquire_badge_image')
    def test_badge_html(self, img_proc):
        img_proc.return_value = 'temp.png'
        badge = {
            'badgeName': get_garbage(),
            'description': get_garbage(),
            'imageurl': get_garbage(),
            'criteria': get_garbage()
        }
        ret = self.app.post_json(api_url_for('create_badge'), badge, auth=self.user.auth)
        self.user_settings.reload()
        assert_equals(ret.status_int, 201)
        assert_equals(ret.content_type, 'application/json')
        assert_true(ret.json['badgeid'] in [badge._id for badge in self.user_settings.badges])
        with self.app.app.test_request_context():
            bstr = str(self.user_settings.badges[0].to_openbadge())
        assert_false('>' in bstr)
        assert_false('<' in bstr)

    def test_revoke_badge(self):
        badgeid = self.user_settings.badges[0]._id
        initnum = get_node_badges(self.project).count()
        assert_true(self.user_settings.can_award)
        url = api_url_for('award_badge', pid=self.project._id)
        ret = self.app.post_json(url, {'badgeid': badgeid}, auth=self.user.auth)
        self.project.reload()
        assert_equals(ret.status_int, 200)
        assert_equals(initnum + 1, get_node_badges(self.project).count())

        assertion = get_node_badges(self.project)[0]

        revoke = api_url_for('revoke_badge', pid=self.project._id)
        ret = self.app.post_json(revoke,
            {
                'id': assertion._id,
                'reason': ''
            }, auth=self.user.auth)
        self.project.reload()
        self.user_settings.reload()
        assertion.reload()

        assert_equals(ret.status_int, 200)
        assert_true(get_node_badges(self.project)[0]._id, assertion._id)
        assert_true(assertion.revoked)
        assert_true(assertion._id in self.user_settings.revocation_list)
        assert_equals(len(self.user_settings.revocation_list), 1)

    def test_revoke_badge_reason(self):
        badgeid = self.user_settings.badges[0]._id
        initnum = get_node_badges(self.project).count()
        assert_true(self.user_settings.can_award)
        url = api_url_for('award_badge', pid=self.project._id)
        ret = self.app.post_json(url, {'badgeid': badgeid}, auth=self.user.auth)
        self.project.reload()
        assert_equals(ret.status_int, 200)
        assert_equals(initnum + 1, get_node_badges(self.project).count())

        assertion = get_node_badges(self.project)[0]

        revoke = api_url_for('revoke_badge', pid=self.project._id)
        ret = self.app.post_json(revoke,
            {
                'id': assertion._id,
                'reason': 'Is a loser'
            }, auth=self.user.auth)
        self.project.reload()
        self.user_settings.reload()
        assertion.reload()

        assert_equals(ret.status_int, 200)
        assert_true(get_node_badges(self.project)[0]._id, assertion._id)
        assert_true(assertion._id in self.user_settings.revocation_list)
        assert_equals(len(self.user_settings.revocation_list), 1)
        assert_true(assertion.revoked)
        assert_equals(self.user_settings.revocation_list[assertion._id], 'Is a loser')

    def test_revoke_badge_no_addon(self):
        badgeid = self.user_settings.badges[0]._id
        initnum = get_node_badges(self.project).count()
        assert_true(self.user_settings.can_award)
        url = api_url_for('award_badge', pid=self.project._id)
        ret = self.app.post_json(url, {'badgeid': badgeid}, auth=self.user.auth)
        self.project.reload()
        assert_equals(ret.status_int, 200)
        assert_equals(initnum + 1, get_node_badges(self.project).count())

        assertion = get_node_badges(self.project)[0]

        revoke = api_url_for('revoke_badge', pid=self.project._id)
        self.user.delete_addon('badges')
        self.user.save()
        self.user.reload()

        ret = self.app.post_json(revoke,
            {
                'id': assertion._id,
                'reason': ''
            }, auth=self.user.auth, expect_errors=True)
        self.project.reload()
        self.user_settings.reload()
        assertion.reload()

        assert_equals(ret.status_int, 400)
        assert_false(assertion.revoked)
        assert_true(get_node_badges(self.project)[0]._id, assertion._id)
        assert_false(assertion._id in self.user_settings.revocation_list)

    def test_revoke_didnt_award(self):
        badgeid = self.user_settings.badges[0]._id
        initnum = get_node_badges(self.project).count()
        assert_true(self.user_settings.can_award)
        url = api_url_for('award_badge', pid=self.project._id)
        ret = self.app.post_json(url, {'badgeid': badgeid}, auth=self.user.auth)
        self.project.reload()
        assert_equals(ret.status_int, 200)
        assert_equals(initnum + 1, get_node_badges(self.project).count())

        assertion = get_node_badges(self.project)[0]

        revoke = api_url_for('revoke_badge', pid=self.project._id)

        user2 = AuthUserFactory()
        user2.add_addon('badges', override=True)
        user2.save()
        user2.reload()

        ret = self.app.post_json(revoke,
            {
                'id': assertion._id,
                'reason': ''
            }, auth=user2.auth, expect_errors=True)
        self.project.reload()
        self.user_settings.reload()
        assertion.reload()

        assert_equals(ret.status_int, 400)
        assert_false(assertion.revoked)
        assert_true(get_node_badges(self.project)[0]._id, assertion._id)
        assert_false(assertion._id in self.user_settings.revocation_list)

    def test_issuer_html(self):
        pass

    def test_revoke_bad_aid(self):
        badgeid = self.user_settings.badges[0]._id
        initnum = get_node_badges(self.project).count()
        assert_true(self.user_settings.can_award)
        url = api_url_for('award_badge', pid=self.project._id)
        ret = self.app.post_json(url, {'badgeid': badgeid}, auth=self.user.auth)
        self.project.reload()
        assert_equals(ret.status_int, 200)
        assert_equals(initnum + 1, get_node_badges(self.project).count())

        assertion = get_node_badges(self.project)[0]

        revoke = api_url_for('revoke_badge', pid=self.project._id)

        ret = self.app.post_json(revoke,
            {
                'id': 'Im a bad id :D',
                'reason': ''
            }, auth=self.user.auth, expect_errors=True)
        self.project.reload()
        self.user_settings.reload()
        assertion.reload()

        assert_equals(ret.status_int, 400)
        assert_false(assertion.revoked)
        assert_true(get_node_badges(self.project)[0]._id, assertion._id)
        assert_false(assertion._id in self.user_settings.revocation_list)

    def test_system_badge_awarder(self):
        badgeid = self.user_settings.badges[0]._id
        self.user_settings.badges[0].make_system_badge()
        initnum = get_node_badges(self.project).count()
        assert_true(self.user_settings.can_award)
        url = api_url_for('award_badge', pid=self.project._id)
        ret = self.app.post_json(url, {'badgeid': badgeid}, auth=self.user.auth)
        self.project.reload()
        assert_equals(ret.status_int, 200)
        assert_equals(initnum + 1, get_node_badges(self.project).count())

        assertion = get_node_badges(self.project)[0]
        assert_equals(assertion.awarder._id, self.user_settings._id)

    def test_badge_awarder(self):
        badgeid = self.user_settings.badges[0]._id
        initnum = get_node_badges(self.project).count()
        assert_true(self.user_settings.can_award)
        url = api_url_for('award_badge', pid=self.project._id)
        ret = self.app.post_json(url, {'badgeid': badgeid}, auth=self.user.auth)
        self.project.reload()
        assert_equals(ret.status_int, 200)
        assert_equals(initnum + 1, get_node_badges(self.project).count())

        assertion = get_node_badges(self.project)[0]
        assert_equals(assertion.awarder._id, self.user_settings._id)

    def test_award_times(self):
        badge = self.user_settings.badges[0]
        assert_true(self.user_settings.can_award)
        url = api_url_for('award_badge', pid=self.project._id)
        ret = self.app.post_json(url, {'badgeid': badge._id}, auth=self.user.auth)
        ret = self.app.post_json(url, {'badgeid': badge._id}, auth=self.user.auth)
        ret = self.app.post_json(url, {'badgeid': badge._id}, auth=self.user.auth)
        self.project.reload()
        assert_equals(ret.status_int, 200)
        badge.reload()
        assert_equals(badge.awarded_count, 3)
        ret = self.app.post_json(url, {'badgeid': badge._id}, auth=self.user.auth)
        ret = self.app.post_json(url, {'badgeid': badge._id}, auth=self.user.auth)
        badge.reload()
        assert_equals(badge.awarded_count, 5)

    def test_unique_awards(self):
        badge = self.user_settings.badges[0]
        assert_true(self.user_settings.can_award)
        url = api_url_for('award_badge', pid=self.project._id)
        ret = self.app.post_json(url, {'badgeid': badge._id}, auth=self.user.auth)
        ret = self.app.post_json(url, {'badgeid': badge._id}, auth=self.user.auth)
        ret = self.app.post_json(url, {'badgeid': badge._id}, auth=self.user.auth)
        self.project.reload()
        assert_equals(ret.status_int, 200)
        badge.reload()
        assert_equals(badge.unique_awards_count, 1)
        ret = self.app.post_json(url, {'badgeid': badge._id}, auth=self.user.auth)
        ret = self.app.post_json(url, {'badgeid': badge._id}, auth=self.user.auth)
        badge.reload()
        assert_equals(badge.unique_awards_count, 1)
