
from unittest.mock import ANY

import time
from unittest import mock

import pytest
from django.core.exceptions import ValidationError
from pytest import approx

from framework import auth
from framework.auth import Auth
from osf.models import (
    NodeRelation, NotificationType,
)
from osf.utils import permissions
from osf_tests.factories import (
    fake_email,
    AuthUserFactory,
    NodeFactory,
    ProjectFactory,
    RegistrationProviderFactory,
    UserFactory,
    UnregUserFactory,
    DraftRegistrationFactory,
)
from tests.base import (
    fake,
    get_default_metaschema,
    OsfTestCase,
)
from tests.utils import capture_notifications
from website import mails, settings
from website.profile.utils import add_contributor_json, serialize_unregistered
from website.project.views.contributor import (
    deserialize_contributors,
    notify_added_contributor,
)

@pytest.mark.enable_implicit_clean
class TestAddingContributorViews(OsfTestCase):

    def setUp(self):
        super().setUp()
        self.creator = AuthUserFactory()
        self.project = ProjectFactory(creator=self.creator)
        self.auth = Auth(self.project.creator)

    def test_serialize_unregistered_without_record(self):
        name, email = fake.name(), fake_email()
        res = serialize_unregistered(fullname=name, email=email)
        assert res['fullname'] == name
        assert res['email'] == email
        assert res['id'] is None
        assert not res['registered']
        assert res['profile_image_url']
        assert not res['active']

    def test_deserialize_contributors(self):
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
        assert len(res) == len(contrib_data)
        assert res[0]['user'].is_registered

        assert not res[1]['user'].is_registered
        assert res[1]['user']._id

        assert not res[2]['user'].is_registered
        assert res[2]['user']._id

    def test_deserialize_contributors_validates_fullname(self):
        name = '<img src=1 onerror=console.log(1)>'
        email = fake_email()
        unreg_no_record = serialize_unregistered(name, email)
        contrib_data = [unreg_no_record]
        contrib_data[0]['permission'] = permissions.ADMIN
        contrib_data[0]['visible'] = True

        with pytest.raises(ValidationError):
            deserialize_contributors(
                self.project,
                contrib_data,
                auth=Auth(self.creator),
                validate=True)

    def test_deserialize_contributors_validates_email(self):
        name = fake.name()
        email = '!@#$%%^&*'
        unreg_no_record = serialize_unregistered(name, email)
        contrib_data = [unreg_no_record]
        contrib_data[0]['permission'] = permissions.ADMIN
        contrib_data[0]['visible'] = True

        with pytest.raises(ValidationError):
            deserialize_contributors(
                self.project,
                contrib_data,
                auth=Auth(self.creator),
                validate=True)

    def test_serialize_unregistered_with_record(self):
        name, email = fake.name(), fake_email()
        user = self.project.add_unregistered_contributor(fullname=name,
                                                         email=email, auth=Auth(self.project.creator))
        self.project.save()
        res = serialize_unregistered(
            fullname=name,
            email=email
        )
        assert not res['active']
        assert not res['registered']
        assert res['id'] == user._primary_key
        assert res['profile_image_url']
        assert res['fullname'] == name
        assert res['email'] == email

    def test_add_contributor_with_unreg_contribs_and_reg_contribs(self):
        n_contributors_pre = len(self.project.contributors)
        reg_user = UserFactory()
        name, email = fake.name(), fake_email()
        pseudouser = {
            'id': None,
            'registered': False,
            'fullname': name,
            'email': email,
            'permission': permissions.ADMIN,
            'visible': True,
        }
        reg_dict = add_contributor_json(reg_user)
        reg_dict['permission'] = permissions.ADMIN
        reg_dict['visible'] = True
        payload = {
            'users': [reg_dict, pseudouser],
            'node_ids': []
        }
        url = self.project.api_url_for('project_contributors_post')
        self.app.post(url, json=payload, follow_redirects=True, auth=self.creator.auth)
        self.project.reload()
        assert len(self.project.contributors) == n_contributors_pre + len(payload['users'])

        new_unreg = auth.get_user(email=email)
        assert not new_unreg.is_registered
        # unclaimed record was added
        new_unreg.reload()
        assert self.project._primary_key in new_unreg.unclaimed_records
        rec = new_unreg.get_unclaimed_record(self.project._primary_key)
        assert rec['name'] == name
        assert rec['email'] == email

    def test_add_contributors_post_only_sends_one_email_to_unreg_user(self):
        # Project has components
        comp1 = NodeFactory(creator=self.creator)
        comp2 = NodeFactory(creator=self.creator)
        NodeRelation.objects.create(parent=self.project, child=comp1)
        NodeRelation.objects.create(parent=self.project, child=comp2)
        self.project.save()

        # An unreg user is added to the project AND its components
        unreg_user = {  # dict because user has not previous unreg record
            'id': None,
            'registered': False,
            'fullname': fake.name(),
            'email': fake_email(),
            'permission': permissions.ADMIN,
            'visible': True,
        }
        payload = {
            'users': [unreg_user],
            'node_ids': [comp1._primary_key, comp2._primary_key]
        }

        # send request
        url = self.project.api_url_for('project_contributors_post')
        assert self.project.can_edit(user=self.creator)
        self.app.post(url, json=payload, auth=self.creator.auth)

        # finalize_invitation should only have been called once
        assert mock_send_claim_email.call_count == 1

    def test_add_contributors_post_only_sends_one_email_to_registered_user(self):
        # Project has components
        comp1 = NodeFactory(creator=self.creator, parent=self.project)
        comp2 = NodeFactory(creator=self.creator, parent=self.project)

        # A registered user is added to the project AND its components
        user = UserFactory()
        assert self.project.can_edit(user=self.creator)

        with capture_notifications() as notifications:
            self.app.post(
                self.project.api_url_for('project_contributors_post'),
                json={
                    'users': [{
                        'id': user._id,
                        'fullname': user.fullname,
                        'email': user.username,
                        'permission': permissions.WRITE,
                        'visible': True
                    }],
                    'node_ids': [comp1._primary_key, comp2._primary_key]
                },
                auth=self.creator.auth
            )

        assert len(notifications) == 1

    def test_add_contributors_post_sends_email_if_user_not_contributor_on_parent_node(self,):
        # Project has a component with a sub-component
        component = NodeFactory(creator=self.creator, parent=self.project)
        sub_component = NodeFactory(creator=self.creator, parent=component)

        # A registered user is added to the project and the sub-component, but NOT the component
        user = UserFactory()
        # send request
        url = self.project.api_url_for('project_contributors_post')
        assert self.project.can_edit(user=self.creator)
        with capture_notifications() as notifications:
            self.app.post(
                url,
                json={
                    'users': [{
                        'id': user._id,
                        'fullname': user.fullname,
                        'email': user.username,
                        'permission': permissions.WRITE,
                        'visible': True
                    }],
                    'node_ids': [sub_component._primary_key]
                },
                auth=self.creator.auth
            )

            # send_mail is called for both the project and the sub-component
        assert len(notifications) == 2
        assert notifications[0]['kwargs']['user'] == user
        assert notifications[0]['type'] == NotificationType.Type.USER_CONTRIBUTOR_ADDED_DEFAULT.value
        assert notifications[1]['kwargs']['user'] == user
        assert notifications[1]['type'] == NotificationType.Type.USER_CONTRIBUTOR_ADDED_DEFAULT.value

    @mock.patch('website.project.views.contributor.send_claim_email')
    def test_email_sent_when_unreg_user_is_added(self, send_mail):
        name, email = fake.name(), fake_email()
        pseudouser = {
            'id': None,
            'registered': False,
            'fullname': name,
            'email': email,
            'permission': permissions.ADMIN,
            'visible': True,
        }
        payload = {
            'users': [pseudouser],
            'node_ids': []
        }
        url = self.project.api_url_for('project_contributors_post')
        self.app.post(url, json=payload, follow_redirects=True, auth=self.creator.auth)
        send_mail.assert_called_with(email, ANY,ANY,notify=True, email_template='default')

    @mock.patch('website.mails.send_mail')
    def test_email_sent_when_reg_user_is_added(self, send_mail):
        contributor = UserFactory()
        contributors = [{
            'user': contributor,
            'visible': True,
            'permissions': permissions.WRITE
        }]
        project = ProjectFactory(creator=self.auth.user)
        project.add_contributors(contributors, auth=self.auth)
        project.save()
        assert send_mail.called
        send_mail.assert_called_with(
            to_addr=contributor.username,
            mail=mails.CONTRIBUTOR_ADDED_DEFAULT,
            user=contributor,
            node=project,
            referrer_name=self.auth.user.fullname,
            all_global_subscriptions_none=False,
            branded_service=None,
            can_change_preferences=False,
            logo=settings.OSF_LOGO,
            osf_contact_email=settings.OSF_CONTACT_EMAIL,
            is_initiator=False,
            published_preprints=[]

        )
        assert contributor.contributor_added_email_records[project._id]['last_sent'] == approx(int(time.time()), rel=1)

    @mock.patch('website.mails.send_mail')
    def test_contributor_added_email_sent_to_unreg_user(self, send_mail):
        unreg_user = UnregUserFactory()
        project = ProjectFactory()
        project.add_unregistered_contributor(fullname=unreg_user.fullname, email=unreg_user.email, auth=Auth(project.creator))
        project.save()
        assert send_mail.called

    @mock.patch('website.mails.send_mail')
    def test_forking_project_does_not_send_contributor_added_email(self, send_mail):
        project = ProjectFactory()
        project.fork_node(auth=Auth(project.creator))
        assert not send_mail.called

    @mock.patch('website.mails.send_mail')
    def test_templating_project_does_not_send_contributor_added_email(self, send_mail):
        project = ProjectFactory()
        project.use_as_template(auth=Auth(project.creator))
        assert not send_mail.called

    @mock.patch('website.archiver.tasks.archive')
    @mock.patch('website.mails.send_mail')
    def test_registering_project_does_not_send_contributor_added_email(self, send_mail, mock_archive):
        project = ProjectFactory()
        provider = RegistrationProviderFactory()
        project.register_node(
            get_default_metaschema(),
            Auth(user=project.creator),
            DraftRegistrationFactory(branched_from=project),
            None,
            provider=provider
        )
        assert not send_mail.called

    def test_notify_contributor_email_does_not_send_before_throttle_expires(self):
        contributor = UserFactory()
        project = ProjectFactory()
        auth = Auth(project.creator)

        with capture_notifications() as notifications:
            notify_added_contributor(project, contributor, auth)
            # 2nd call does not send email because throttle period has not expired
            notify_added_contributor(project, contributor, auth)
        assert len(notifications) == 1

    def test_notify_contributor_email_sends_after_throttle_expires(self):
        contributor = UserFactory()
        project = ProjectFactory()
        auth = Auth(project.creator)

        with capture_notifications() as notifications:
            notify_added_contributor(project, contributor, auth)

        assert notifications[0]['type'] == NotificationType.Type.USER_CONTRIBUTOR_ADDED_DEFAULT.value

    def test_add_contributor_to_fork_sends_email(self):
        contributor = UserFactory()
        fork = self.project.fork_node(auth=Auth(self.creator))
        with capture_notifications() as notifications:
            fork.add_contributor(contributor, auth=Auth(self.creator))
            fork.save()

        assert len(notifications) == 1
        assert notifications[0]['kwargs']['user'] == contributor
        assert notifications[0]['type'] == NotificationType.Type.USER_CONTRIBUTOR_ADDED_DEFAULT.value

    def test_add_contributor_to_template_sends_email(self):
        contributor = UserFactory()
        template = self.project.use_as_template(auth=Auth(self.creator))
        with capture_notifications() as notifications:
            template.add_contributor(contributor, auth=Auth(self.creator))
            template.save()

        assert len(notifications) == 1
        assert notifications[0]['type'] == NotificationType.Type.USER_CONTRIBUTOR_ADDED_DEFAULT
        assert notifications[0]['kwargs']['user'] == contributor

    def test_creating_fork_does_not_email_creator(self):
        contributor = UserFactory()
        template = self.project.use_as_template(auth=Auth(self.creator))
        with capture_notifications() as notifications:
            template.add_contributor(contributor, auth=Auth(self.creator))
            template.save()
        assert not notifications

    def test_creating_template_does_not_email_creator(self):
        with capture_notifications() as notifications:
            self.project.use_as_template(auth=Auth(self.creator))
        assert not notifications

    def test_add_multiple_contributors_only_adds_one_log(self):
        n_logs_pre = self.project.logs.count()
        reg_user = UserFactory()
        name = fake.name()
        self.app.post(
            self.project.api_url_for('project_contributors_post'),
            json={
                'users': [
                    {
                        'permission': permissions.ADMIN,
                        'visible': True,
                        **add_contributor_json(reg_user)
                    },
                    {
                        'id': None,
                        'registered': False,
                        'fullname': name,
                        'email': fake_email(),
                        'permission': permissions.WRITE,
                        'visible': True,
                    }
                ],
                'node_ids': []
            },
            follow_redirects=True,
            auth=self.creator.auth
        )
        self.project.reload()
        assert self.project.logs.count() == n_logs_pre + 1

    def test_add_contribs_to_multiple_nodes(self):
        child = NodeFactory(parent=self.project, creator=self.creator)
        n_contributors_pre = child.contributors.count()
        reg_user = UserFactory()
        name, email = fake.name(), fake_email()
        self.app.post(
            f'/api/v1/project/{self.project._id}/contributors/',
            json={
                'users': [
                    {
                        'permission': permissions.ADMIN,
                        'visible': True,
                        **add_contributor_json(reg_user)
                    },
                    {
                        'id': None,
                        'registered': False,
                        'fullname': name,
                        'email': email,
                        'permission': permissions.ADMIN,
                        'visible': True,
                    }
                ],
                'node_ids': [self.project._primary_key, child._primary_key]
            },
            follow_redirects=True,
            auth=self.creator.auth
        )
        child.reload()
        assert child.contributors.count() == n_contributors_pre + 2  # 2 users in payload
