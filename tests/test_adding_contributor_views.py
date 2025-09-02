import time
from unittest import mock

import pytest
from django.core.exceptions import ValidationError
from rest_framework import status as http_status

from framework import auth
from framework.auth import Auth
from framework.exceptions import HTTPError
from osf.models import NodeRelation, NotificationType
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
from website.profile.utils import add_contributor_json, serialize_unregistered
from website.project.views.contributor import (
    deserialize_contributors,
    notify_added_contributor,
    send_claim_email,
)

@pytest.mark.enable_implicit_clean
@mock.patch('website.mails.settings.USE_EMAIL', True)
@mock.patch('website.mails.settings.USE_CELERY', False)
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
        with capture_notifications():
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

    @mock.patch('website.project.views.contributor.send_claim_email')
    def test_add_contributors_post_only_sends_one_email_to_unreg_user(self, mock_send_claim_email):
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
        with capture_notifications() as notifications:
            self.app.post(url, json=payload, auth=self.creator.auth)
        assert len(notifications['emits']) == 1
        assert notifications['emits'][0]['type'] == NotificationType.Type.NODE_CONTRIBUTOR_ADDED_DEFAULT

    def test_add_contributors_post_only_sends_one_email_to_registered_user(self):
        # Project has components
        comp1 = NodeFactory(creator=self.creator, parent=self.project)
        comp2 = NodeFactory(creator=self.creator, parent=self.project)

        # A registered user is added to the project AND its components
        user = UserFactory()
        user_dict = {
            'id': user._id,
            'fullname': user.fullname,
            'email': user.username,
            'permission': permissions.WRITE,
            'visible': True}

        payload = {
            'users': [user_dict],
            'node_ids': [comp1._primary_key, comp2._primary_key]
        }

        # send request
        url = self.project.api_url_for('project_contributors_post')
        assert self.project.can_edit(user=self.creator)
        with capture_notifications() as notifications:
            self.app.post(url, json=payload, auth=self.creator.auth)
        assert len(notifications['emits']) == 1
        assert notifications['emits'][0]['type'] == NotificationType.Type.NODE_CONTRIBUTOR_ADDED_DEFAULT

    def test_add_contributors_post_sends_email_if_user_not_contributor_on_parent_node(self):
        # Project has a component with a sub-component
        component = NodeFactory(creator=self.creator, parent=self.project)
        sub_component = NodeFactory(creator=self.creator, parent=component)

        # A registered user is added to the project and the sub-component, but NOT the component
        user = UserFactory()
        user_dict = {
            'id': user._id,
            'fullname': user.fullname,
            'email': user.username,
            'permission': permissions.WRITE,
            'visible': True}

        payload = {
            'users': [user_dict],
            'node_ids': [sub_component._primary_key]
        }

        # send request
        url = self.project.api_url_for('project_contributors_post')
        assert self.project.can_edit(user=self.creator)
        with capture_notifications() as notifications:
            self.app.post(url, json=payload, auth=self.creator.auth)

        # send_mail is called for both the project and the sub-component
        assert len(notifications['emits']) == 1
        assert notifications['emits'][0]['type'] == NotificationType.Type.NODE_CONTRIBUTOR_ADDED_DEFAULT

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
        with capture_notifications() as notifications:
            self.app.post(url, json=payload, follow_redirects=True, auth=self.creator.auth)
        assert len(notifications['emits']) == 1
        assert notifications['emits'][0]['type'] == NotificationType.Type.NODE_CONTRIBUTOR_ADDED_DEFAULT

    def test_email_sent_when_reg_user_is_added(self):
        contributor = UserFactory()
        contributors = [{
            'user': contributor,
            'visible': True,
            'permissions': permissions.WRITE
        }]
        project = ProjectFactory(creator=self.auth.user)
        with capture_notifications() as notifications:
            project.add_contributors(contributors, auth=self.auth)
            project.save()
        assert len(notifications['emits']) == 1
        assert notifications['emits'][0]['type'] == NotificationType.Type.NODE_CONTRIBUTOR_ADDED_DEFAULT

    def test_contributor_added_email_sent_to_unreg_user(self):
        unreg_user = UnregUserFactory()
        project = ProjectFactory()
        project.add_unregistered_contributor(fullname=unreg_user.fullname, email=unreg_user.email, auth=Auth(project.creator))
        project.save()

    def test_forking_project_does_not_send_contributor_added_email(self):
        project = ProjectFactory()
        with capture_notifications():
            project.fork_node(auth=Auth(project.creator))

    def test_templating_project_does_not_send_contributor_added_email(self):
        project = ProjectFactory()
        with capture_notifications():
            project.use_as_template(auth=Auth(project.creator))

    @mock.patch('website.archiver.tasks.archive')
    def test_registering_project_does_not_send_contributor_added_email(self, mock_archive):
        project = ProjectFactory()
        provider = RegistrationProviderFactory()
        project.register_node(
            get_default_metaschema(),
            Auth(user=project.creator),
            DraftRegistrationFactory(branched_from=project),
            None,
            provider=provider
        )

    def test_notify_contributor_email_does_not_send_before_throttle_expires(self):
        contributor = UserFactory()
        project = ProjectFactory()
        auth = Auth(project.creator)
        with capture_notifications() as notifications:
            notify_added_contributor(
                project,
                contributor,
                notification_type=NotificationType.Type.NODE_CONTRIBUTOR_ADDED_DEFAULT,
                auth=auth
            )
        assert len(notifications['emits']) == 1
        assert notifications['emits'][0]['type'] == NotificationType.Type.NODE_CONTRIBUTOR_ADDED_DEFAULT

        # 2nd call does not send email because throttle period has not expired
        notify_added_contributor(
            project,
            contributor,
            notification_type=NotificationType.Type.NODE_CONTRIBUTOR_ADDED_DEFAULT,
            auth=auth
        )

    def test_notify_contributor_email_sends_after_throttle_expires(self):
        contributor = UserFactory()
        project = ProjectFactory()
        auth = Auth(project.creator)
        with capture_notifications() as notifications:
            notify_added_contributor(
                project,
                contributor,
                NotificationType.Type.NODE_CONTRIBUTOR_ADDED_DEFAULT,
                auth,
            )
        assert len(notifications['emits']) == 1
        assert notifications['emits'][0]['type'] == NotificationType.Type.NODE_CONTRIBUTOR_ADDED_DEFAULT

        time.sleep(2)  # throttle period expires
        with capture_notifications() as notifications:
            notify_added_contributor(
                project,
                contributor,
                NotificationType.Type.NODE_CONTRIBUTOR_ADDED_DEFAULT,
                auth,
                throttle=1
            )
        assert len(notifications['emits']) == 1
        assert notifications['emits'][0]['type'] == NotificationType.Type.NODE_CONTRIBUTOR_ADDED_DEFAULT

    def test_add_contributor_to_fork_sends_email(self):
        contributor = UserFactory()
        with capture_notifications() as notifications:
            fork = self.project.fork_node(auth=Auth(self.creator))
            fork.add_contributor(contributor, auth=Auth(self.creator))
            fork.save()
        assert len(notifications['emits']) == 1
        assert notifications['emits'][0]['type'] == NotificationType.Type.NODE_CONTRIBUTOR_ADDED_DEFAULT

    def test_add_contributor_to_template_sends_email(self):
        contributor = UserFactory()
        with capture_notifications() as notifications:
            template = self.project.use_as_template(auth=Auth(self.creator))
            template.add_contributor(
                contributor,
                auth=Auth(self.creator),
                notification_type=NotificationType.Type.NODE_CONTRIBUTOR_ADDED_DEFAULT
            )
            template.save()
        assert len(notifications['emits']) == 2
        assert notifications['emits'][0]['type'] == NotificationType.Type.NODE_CONTRIBUTOR_ADDED_ACCESS_REQUEST

    def test_creating_fork_does_not_email_creator(self):
        with capture_notifications():
            self.project.fork_node(auth=Auth(self.creator))

    def test_creating_template_does_not_email_creator(self):
        with capture_notifications():
            self.project.use_as_template(auth=Auth(self.creator))

    def test_add_multiple_contributors_only_adds_one_log(self):
        n_logs_pre = self.project.logs.count()
        reg_user = UserFactory()
        name = fake.name()
        pseudouser = {
            'id': None,
            'registered': False,
            'fullname': name,
            'email': fake_email(),
            'permission': permissions.WRITE,
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
        with capture_notifications():
            self.app.post(url, json=payload, follow_redirects=True, auth=self.creator.auth)
        self.project.reload()
        assert self.project.logs.count() == n_logs_pre + 1

    def test_add_contribs_to_multiple_nodes(self):
        child = NodeFactory(parent=self.project, creator=self.creator)
        n_contributors_pre = child.contributors.count()
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
            'node_ids': [self.project._primary_key, child._primary_key]
        }
        url = f'/api/v1/project/{self.project._id}/contributors/'
        with capture_notifications():
            self.app.post(url, json=payload, follow_redirects=True, auth=self.creator.auth)
        child.reload()
        assert child.contributors.count() == n_contributors_pre + len(payload['users'])


@mock.patch('website.mails.settings.USE_EMAIL', True)
@mock.patch('website.mails.settings.USE_CELERY', False)
class TestUserInviteViews(OsfTestCase):

    def setUp(self):
        super().setUp()
        self.user = AuthUserFactory()
        self.project = ProjectFactory(creator=self.user)
        self.invite_url = f'/api/v1/project/{self.project._primary_key}/invite_contributor/'

    def test_invite_contributor_post_if_not_in_db(self):
        name, email = fake.name(), fake_email()
        res = self.app.post(
            self.invite_url,
            json={'fullname': name, 'email': email},
            auth=self.user.auth,
        )
        contrib = res.json['contributor']
        assert contrib['id'] is None
        assert contrib['fullname'] == name
        assert contrib['email'] == email

    def test_invite_contributor_post_if_unreg_already_in_db(self):
        # A n unreg user is added to a different project
        name, email = fake.name(), fake_email()
        project2 = ProjectFactory()
        unreg_user = project2.add_unregistered_contributor(fullname=name, email=email,
                                                           auth=Auth(project2.creator))
        project2.save()
        res = self.app.post(self.invite_url,
                                 json={'fullname': name, 'email': email}, auth=self.user.auth)
        expected = add_contributor_json(unreg_user)
        expected['fullname'] = name
        expected['email'] = email
        assert res.json['contributor'] == expected

    def test_invite_contributor_post_if_email_already_registered(self):
        reg_user = UserFactory()
        name, email = fake.name(), reg_user.username
        # Tries to invite user that is already registered - this is now permitted.
        res = self.app.post(self.invite_url,
                                 json={'fullname': name, 'email': email},
                                 auth=self.user.auth)
        contrib = res.json['contributor']
        assert contrib['id'] == reg_user._id
        assert contrib['fullname'] == name
        assert contrib['email'] == email

    def test_invite_contributor_post_if_user_is_already_contributor(self):
        unreg_user = self.project.add_unregistered_contributor(
            fullname=fake.name(), email=fake_email(),
            auth=Auth(self.project.creator)
        )
        self.project.save()
        # Tries to invite unreg user that is already a contributor
        res = self.app.post(self.invite_url,
                                 json={'fullname': fake.name(), 'email': unreg_user.username},
                                 auth=self.user.auth)
        assert res.status_code == http_status.HTTP_400_BAD_REQUEST

    def test_invite_contributor_with_no_email(self):
        name = fake.name()
        res = self.app.post(self.invite_url,
                                 json={'fullname': name, 'email': None}, auth=self.user.auth)
        assert res.status_code == http_status.HTTP_200_OK
        data = res.json
        assert data['status'] == 'success'
        assert data['contributor']['fullname'] == name
        assert data['contributor']['email'] is None
        assert not data['contributor']['registered']

    def test_invite_contributor_requires_fullname(self):
        res = self.app.post(self.invite_url,
                                 json={'email': 'brian@queen.com', 'fullname': ''}, auth=self.user.auth,
                                 )
        assert res.status_code == http_status.HTTP_400_BAD_REQUEST

    def test_send_claim_email_to_given_email(self):
        project = ProjectFactory()
        given_email = fake_email()
        unreg_user = project.add_unregistered_contributor(
            fullname=fake.name(),
            email=given_email,
            auth=Auth(project.creator),
        )
        project.save()
        with capture_notifications() as notifications:
            send_claim_email(email=given_email, unclaimed_user=unreg_user, node=project)
        assert len(notifications['emits']) == 1
        assert notifications['emits'][0]['type'] == NotificationType.Type.USER_INVITE_DEFAULT

    def test_send_claim_email_to_referrer(self):
        project = ProjectFactory()
        referrer = project.creator
        given_email, real_email = fake_email(), fake_email()
        unreg_user = project.add_unregistered_contributor(
            fullname=fake.name(),
            email=given_email,
            auth=Auth(referrer)
        )
        project.save()
        with capture_notifications() as notifications:
            send_claim_email(email=real_email, unclaimed_user=unreg_user, node=project)

        assert len(notifications['emits']) == 2
        assert notifications['emits'][0]['type'] == NotificationType.Type.USER_PENDING_VERIFICATION
        assert notifications['emits'][1]['type'] ==  NotificationType.Type.USER_FORWARD_INVITE

    def test_send_claim_email_before_throttle_expires(self):
        project = ProjectFactory()
        given_email = fake_email()
        unreg_user = project.add_unregistered_contributor(
            fullname=fake.name(),
            email=given_email,
            auth=Auth(project.creator),
        )
        project.save()
        with capture_notifications():
            send_claim_email(email=fake_email(), unclaimed_user=unreg_user, node=project)
        # 2nd call raises error because throttle hasn't expired

        with pytest.raises(HTTPError):
            send_claim_email(email=fake_email(), unclaimed_user=unreg_user, node=project)
