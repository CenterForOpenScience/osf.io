from __future__ import absolute_import
import json
import mock
import pytest
from nose.tools import *
from framework.auth import Auth
from osf.utils import permissions
from tests.base import (
    fake,
    OsfTestCase,
)
from website.profile.utils import add_contributor_json, serialize_unregistered
from website.project.signals import contributor_added
from website.project.views.contributor import (
    deserialize_contributors,
    notify_added_contributor,
)
from osf_tests.factories import (
    fake_email,
    AuthUserFactory,
    ProjectFactory,
    UserFactory,
    UnregUserFactory,
)

pytestmark = pytest.mark.django_db


@pytest.mark.enable_bookmark_creation
class TestProjectViews(OsfTestCase):

    def setUp(self):
        super(TestProjectViews, self).setUp()
        self.user1 = AuthUserFactory()
        self.user1.save()
        self.consolidate_auth1 = Auth(user=self.user1)
        self.auth = self.user1.auth
        self.user2 = AuthUserFactory()
        self.auth2 = self.user2.auth
        # A project has 2 contributors
        self.project = ProjectFactory(
            title='Ham',
            description='Honey-baked',
            creator=self.user1
        )
        self.project.add_contributor(self.user2, auth=Auth(self.user1))
        self.project.save()

        self.project2 = ProjectFactory(
            title='Tofu',
            description='Glazed',
            creator=self.user1
        )
        self.project2.add_contributor(self.user2, auth=Auth(self.user1))
        self.project2.save()

    @mock.patch('website.project.views.contributor.finalize_invitation')
    def test_project_contributor_re_invite(self, mock_finalize_invitation):
        url = self.project.api_url_for('project_contributor_re_invite')
        payload = {'guid': self.user2._id}
        self.app.post(url, json.dumps(payload),
                      content_type='application/json',
                      auth=self.auth).maybe_follow()
        self.project.reload()
        mock_finalize_invitation.assert_called()


class TestUserInviteViews(OsfTestCase):
    def setUp(self):
        super(TestUserInviteViews, self).setUp()
        self.user = AuthUserFactory()
        self.project = ProjectFactory(creator=self.user)
        self.invite_url = '/api/v1/project/{0}/invite_contributor/'.format(
            self.project._primary_key
        )

    def test_claim_user_activate(self):
        self.referrer = AuthUserFactory()
        self.project = ProjectFactory(creator=self.referrer, is_public=True)

        given_email = fake_email()
        unreg_user = self.project.add_unregistered_contributor(
            fullname=fake.name(),
            email=given_email,
            auth=Auth(self.project.creator),
        )
        unreg_user.save()

        claim_url = '/user/{uid}/{pid}/claim/activate'.format(
            uid=unreg_user._id,
            pid=self.project._id,
        )
        res = self.app.get(claim_url)
        assert_equal(res.status_code, 200)


class TestConfirmationViewBlockBingPreview(OsfTestCase):

    def setUp(self):
        super(TestConfirmationViewBlockBingPreview, self).setUp()
        self.user_agent = 'Mozilla/5.0 (Windows NT 6.1; WOW64)' \
                          ' AppleWebKit/534+ (KHTML, like Gecko) ' \
                          'BingPreview/1.0b'

    def test_claim_user_form_cancel_request(self):
        referrer = AuthUserFactory()
        project = ProjectFactory(creator=referrer, is_public=True)
        given_name = fake.name()
        given_email = fake_email()
        user = project.add_unregistered_contributor(
            fullname=given_name,
            email=given_email,
            auth=Auth(user=referrer)
        )
        project.save()

        claim_url = user.get_claim_url(project._primary_key)
        res = self.app.get(
            claim_url,
            {
                'cancel': 'true'
            },
            expect_errors=True,
        )
        assert_equal(res.status_code, 302)

    def test_claim_user_form_contributor_is_none(self):
        referrer = AuthUserFactory()
        project = ProjectFactory(creator=referrer, is_public=True)
        given_name = fake.name()
        given_email = fake_email()
        user = project.add_unregistered_contributor(
            fullname=given_name,
            email=given_email,
            auth=Auth(user=referrer)
        )
        claim_url = user.get_claim_url(project._primary_key)
        claim_url = claim_url.replace(user._id, 'abcde')
        res = self.app.get(
            claim_url,
            {
                'cancel': 'true',
            },
            expect_errors=True,
        )
        assert_equal(res.status_code, 400)

    @mock.patch('osf.models.node.Node.cancel_invite')
    def test_claim_user_form_not_nodes_removed(self, mock):
        mock.return_value = False
        referrer = AuthUserFactory()
        project = ProjectFactory(creator=referrer, is_public=True)
        given_name = fake.name()
        given_email = fake_email()
        user = project.add_unregistered_contributor(
            fullname=given_name,
            email=given_email,
            auth=Auth(user=referrer)
        )
        claim_url = user.get_claim_url(project._primary_key)
        res = self.app.get(
            claim_url,
            {
                'cancel': 'true',
            },
            expect_errors=True,
        )
        assert_equal(res.status_code, 400)


@pytest.mark.enable_implicit_clean
class TestAddingContributorViews(OsfTestCase):

    def setUp(self):
        super(TestAddingContributorViews, self).setUp()
        self.creator = AuthUserFactory()
        self.project = ProjectFactory(creator=self.creator)
        self.auth = Auth(self.project.creator)
        # Authenticate all requests
        self.app.authenticate(*self.creator.auth)
        contributor_added.connect(notify_added_contributor)

    def test_deserialize_contributors_temp_account(self):
        contrib = UserFactory()
        unreg = UnregUserFactory()
        name, email = fake.name(), fake_email()
        unreg_no_record = serialize_unregistered(name, email)
        contrib_data = [
            add_contributor_json(contrib),
            serialize_unregistered(fake.name(), unreg.username),
            unreg_no_record
        ]
        contrib_data[0]['permission'] = permissions.ADMIN
        contrib_data[1]['permission'] = permissions.WRITE
        contrib_data[2]['permission'] = permissions.READ
        contrib_data[0]['visible'] = True
        contrib_data[1]['visible'] = True
        contrib_data[2]['visible'] = True
        res = deserialize_contributors(
            self.project,
            contrib_data,
            auth=Auth(self.creator))
        assert_equal(len(res), len(contrib_data))
        assert_true(res[0]['user'].is_registered)

        assert_false(res[1]['user'].is_registered)
        assert_true(res[1]['user']._id)

        assert_false(res[2]['user'].is_registered)
        assert_true(res[2]['user']._id)
