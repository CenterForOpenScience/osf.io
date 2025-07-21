
from unittest.mock import ANY

import time
from http.cookies import SimpleCookie
from unittest import mock

import pytest
from django.core.exceptions import ValidationError
from flask import g
from pytest import approx
from rest_framework import status as http_status

from framework import auth
from framework.auth import Auth, authenticate, cas
from framework.auth.utils import impute_names_model
from framework.exceptions import HTTPError
from framework.flask import redirect
from osf.models import (
    OSFUser,
    Tag,
    NodeRelation,
)
from osf.utils import permissions
from osf_tests.factories import (
    fake_email,
    AuthUserFactory,
    NodeFactory,
    PreprintFactory,
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
from tests.test_cas_authentication import generate_external_user_with_resp
from website import settings
from website.profile.utils import add_contributor_json, serialize_unregistered
from website.project.signals import contributor_added
from website.project.views.contributor import (
    deserialize_contributors,
    notify_added_contributor,
    send_claim_email,
    send_claim_registered_email,
)
from website.util.metrics import OsfSourceTags, OsfClaimedTags, provider_source_tag, provider_claimed_tag
from conftest import start_mock_notification_send

@pytest.mark.enable_implicit_clean
@mock.patch('website.mails.settings.USE_EMAIL', True)
@mock.patch('website.mails.settings.USE_CELERY', False)
class TestAddingContributorViews(OsfTestCase):

    def setUp(self):
        super().setUp()
        self.creator = AuthUserFactory()
        self.project = ProjectFactory(creator=self.creator)
        self.auth = Auth(self.project.creator)
        # Authenticate all requests
        contributor_added.connect(notify_added_contributor)

        self.mock_notification_send = start_mock_notification_send(self)

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

    @mock.patch('website.project.views.contributor.send_claim_email')
    def test_add_contributors_post_only_sends_one_email_to_unreg_user(
            self, mock_send_claim_email):
        # Project has components
        comp1, comp2 = NodeFactory(
            creator=self.creator), NodeFactory(creator=self.creator)
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
        self.app.post(url, json=payload, auth=self.creator.auth)

        # send_mail should only have been called once
        assert self.mock_notification_send.call_count == 1

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
        self.app.post(url, json=payload, auth=self.creator.auth)

        # send_mail is called for both the project and the sub-component
        assert self.mock_notification_send.call_count == 2

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

    def test_email_sent_when_reg_user_is_added(self):
        contributor = UserFactory()
        contributors = [{
            'user': contributor,
            'visible': True,
            'permissions': permissions.WRITE
        }]
        project = ProjectFactory(creator=self.auth.user)
        project.add_contributors(contributors, auth=self.auth)
        project.save()
        assert self.mock_notification_send.called
        contributor.refresh_from_db()
        assert contributor.contributor_added_email_records[project._id]['last_sent'] == approx(int(time.time()), rel=1)

    def test_contributor_added_email_sent_to_unreg_user(self):
        unreg_user = UnregUserFactory()
        project = ProjectFactory()
        project.add_unregistered_contributor(fullname=unreg_user.fullname, email=unreg_user.email, auth=Auth(project.creator))
        project.save()
        assert self.mock_notification_send.called

    def test_forking_project_does_not_send_contributor_added_email(self):
        project = ProjectFactory()
        project.fork_node(auth=Auth(project.creator))
        assert not self.mock_notification_send.called

    def test_templating_project_does_not_send_contributor_added_email(self):
        project = ProjectFactory()
        project.use_as_template(auth=Auth(project.creator))
        assert not self.mock_notification_send.called

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
        assert not self.mock_notification_send.called

    def test_notify_contributor_email_does_not_send_before_throttle_expires(self):
        contributor = UserFactory()
        project = ProjectFactory()
        auth = Auth(project.creator)
        notify_added_contributor(project, contributor, auth)
        assert self.mock_notification_send.called

        # 2nd call does not send email because throttle period has not expired
        notify_added_contributor(project, contributor, auth)
        assert self.mock_notification_send.call_count == 1

    def test_notify_contributor_email_sends_after_throttle_expires(self):
        throttle = 0.5

        contributor = UserFactory()
        project = ProjectFactory()
        auth = Auth(project.creator)
        notify_added_contributor(project, contributor, auth, throttle=throttle)
        assert self.mock_notification_send.called

        time.sleep(1)  # throttle period expires
        notify_added_contributor(project, contributor, auth, throttle=throttle)
        assert self.mock_notification_send.call_count == 2

    def test_add_contributor_to_fork_sends_email(self):
        contributor = UserFactory()
        fork = self.project.fork_node(auth=Auth(self.creator))
        fork.add_contributor(contributor, auth=Auth(self.creator))
        fork.save()
        assert self.mock_notification_send.called
        assert self.mock_notification_send.call_count == 1

    def test_add_contributor_to_template_sends_email(self):
        contributor = UserFactory()
        template = self.project.use_as_template(auth=Auth(self.creator))
        template.add_contributor(contributor, auth=Auth(self.creator))
        template.save()
        assert self.mock_notification_send.called
        assert self.mock_notification_send.call_count == 1

    def test_creating_fork_does_not_email_creator(self):
        contributor = UserFactory()
        fork = self.project.fork_node(auth=Auth(self.creator))
        assert not self.mock_notification_send.called

    def test_creating_template_does_not_email_creator(self):
        contributor = UserFactory()
        template = self.project.use_as_template(auth=Auth(self.creator))
        assert not self.mock_notification_send.called

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

        self.mock_notification_send = start_mock_notification_send(self)

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
        send_claim_email(email=given_email, unclaimed_user=unreg_user, node=project)

        self.mock_notification_send.assert_called()

    def test_send_claim_email_to_referrer(self):
        project = ProjectFactory()
        referrer = project.creator
        given_email, real_email = fake_email(), fake_email()
        unreg_user = project.add_unregistered_contributor(fullname=fake.name(),
                                                          email=given_email, auth=Auth(
                                                              referrer)
                                                          )
        project.save()
        send_claim_email(email=real_email, unclaimed_user=unreg_user, node=project)

        assert self.mock_notification_send.called

    def test_send_claim_email_before_throttle_expires(self):
        project = ProjectFactory()
        given_email = fake_email()
        unreg_user = project.add_unregistered_contributor(
            fullname=fake.name(),
            email=given_email,
            auth=Auth(project.creator),
        )
        project.save()
        send_claim_email(email=fake_email(), unclaimed_user=unreg_user, node=project)
        self.mock_notification_send.reset_mock()
        # 2nd call raises error because throttle hasn't expired
        with pytest.raises(HTTPError):
            send_claim_email(email=fake_email(), unclaimed_user=unreg_user, node=project)
        assert not self.mock_notification_send.called


@pytest.mark.enable_implicit_clean
@mock.patch('website.mails.settings.USE_EMAIL', True)
@mock.patch('website.mails.settings.USE_CELERY', False)
class TestClaimViews(OsfTestCase):

    def setUp(self):
        super().setUp()
        self.referrer = AuthUserFactory()
        self.project = ProjectFactory(creator=self.referrer, is_public=True)
        self.project_with_source_tag = ProjectFactory(creator=self.referrer, is_public=True)
        self.preprint_with_source_tag = PreprintFactory(creator=self.referrer, is_public=True)
        osf_source_tag, created = Tag.all_tags.get_or_create(name=OsfSourceTags.Osf.value, system=True)
        preprint_source_tag, created = Tag.all_tags.get_or_create(name=provider_source_tag(self.preprint_with_source_tag.provider._id, 'preprint'), system=True)
        self.project_with_source_tag.add_system_tag(osf_source_tag.name)
        self.preprint_with_source_tag.add_system_tag(preprint_source_tag.name)
        self.given_name = fake.name()
        self.given_email = fake_email()
        self.project_with_source_tag.add_unregistered_contributor(
            fullname=self.given_name,
            email=self.given_email,
            auth=Auth(user=self.referrer)
        )
        self.preprint_with_source_tag.add_unregistered_contributor(
            fullname=self.given_name,
            email=self.given_email,
            auth=Auth(user=self.referrer)
        )
        self.user = self.project.add_unregistered_contributor(
            fullname=self.given_name,
            email=self.given_email,
            auth=Auth(user=self.referrer)
        )
        self.project.save()

        self.mock_notification_send = start_mock_notification_send(self)

    @mock.patch('website.project.views.contributor.send_claim_email')
    def test_claim_user_already_registered_redirects_to_claim_user_registered(self, claim_email):
        name = fake.name()
        email = fake_email()

        # project contributor adds an unregistered contributor (without an email) on public project
        unregistered_user = self.project.add_unregistered_contributor(
            fullname=name,
            email=None,
            auth=Auth(user=self.referrer)
        )
        assert unregistered_user in self.project.contributors

        # unregistered user comes along and claims themselves on the public project, entering an email
        invite_url = self.project.api_url_for('claim_user_post', uid='undefined')
        self.app.post(invite_url, json={
            'pk': unregistered_user._primary_key,
            'value': email
        })
        assert claim_email.call_count == 1

        # set unregistered record email since we are mocking send_claim_email()
        unclaimed_record = unregistered_user.get_unclaimed_record(self.project._primary_key)
        unclaimed_record.update({'email': email})
        unregistered_user.save()

        # unregistered user then goes and makes an account with same email, before claiming themselves as contributor
        UserFactory(username=email, fullname=name)

        # claim link for the now registered email is accessed while not logged in
        token = unregistered_user.get_unclaimed_record(self.project._primary_key)['token']
        claim_url = f'/user/{unregistered_user._id}/{self.project._id}/claim/?token={token}'
        res = self.app.get(claim_url)

        # should redirect to 'claim_user_registered' view
        claim_registered_url = f'/user/{unregistered_user._id}/{self.project._id}/claim/verify/{token}/'
        assert res.status_code == 302
        assert claim_registered_url in res.headers.get('Location')

    @mock.patch('website.project.views.contributor.send_claim_email')
    def test_claim_user_already_registered_secondary_email_redirects_to_claim_user_registered(self, claim_email):
        name = fake.name()
        email = fake_email()
        secondary_email = fake_email()

        # project contributor adds an unregistered contributor (without an email) on public project
        unregistered_user = self.project.add_unregistered_contributor(
            fullname=name,
            email=None,
            auth=Auth(user=self.referrer)
        )
        assert unregistered_user in self.project.contributors

        # unregistered user comes along and claims themselves on the public project, entering an email
        invite_url = self.project.api_url_for('claim_user_post', uid='undefined')
        self.app.post(invite_url, json={
            'pk': unregistered_user._primary_key,
            'value': secondary_email
        })
        assert claim_email.call_count == 1

        # set unregistered record email since we are mocking send_claim_email()
        unclaimed_record = unregistered_user.get_unclaimed_record(self.project._primary_key)
        unclaimed_record.update({'email': secondary_email})
        unregistered_user.save()

        # unregistered user then goes and makes an account with same email, before claiming themselves as contributor
        registered_user = UserFactory(username=email, fullname=name)
        registered_user.emails.create(address=secondary_email)
        registered_user.save()

        # claim link for the now registered email is accessed while not logged in
        token = unregistered_user.get_unclaimed_record(self.project._primary_key)['token']
        claim_url = f'/user/{unregistered_user._id}/{self.project._id}/claim/?token={token}'
        res = self.app.get(claim_url)

        # should redirect to 'claim_user_registered' view
        claim_registered_url = f'/user/{unregistered_user._id}/{self.project._id}/claim/verify/{token}/'
        assert res.status_code == 302
        assert claim_registered_url in res.headers.get('Location')

    def test_claim_user_invited_with_no_email_posts_to_claim_form(self):
        given_name = fake.name()
        invited_user = self.project.add_unregistered_contributor(
            fullname=given_name,
            email=None,
            auth=Auth(user=self.referrer)
        )
        self.project.save()

        url = invited_user.get_claim_url(self.project._primary_key)
        res = self.app.post(url, data={
            'password': 'bohemianrhap',
            'password2': 'bohemianrhap'
        })
        assert res.status_code == 400

    def test_claim_user_post_with_registered_user_id(self):
        # registered user who is attempting to claim the unclaimed contributor
        reg_user = UserFactory()
        payload = {
            # pk of unreg user record
            'pk': self.user._primary_key,
            'claimerId': reg_user._primary_key
        }
        url = f'/api/v1/user/{self.user._primary_key}/{self.project._primary_key}/claim/email/'
        res = self.app.post(url, json=payload)

        # mail was sent
        assert self.mock_notification_send.call_count == 2
        # ... to the correct address
        referrer_call = self.mock_notification_send.call_args_list[0]
        claimer_call = self.mock_notification_send.call_args_list[1]

        assert referrer_call[1]['to_addr'] == self.referrer.email
        assert claimer_call[1]['to_addr'] == reg_user.email

        # view returns the correct JSON
        assert res.json == {
            'status': 'success',
            'email': reg_user.username,
            'fullname': self.given_name,
        }

    def test_send_claim_registered_email(self):
        reg_user = UserFactory()
        send_claim_registered_email(
            claimer=reg_user,
            unclaimed_user=self.user,
            node=self.project
        )
        assert self.mock_notification_send.call_count == 2
        first_call_args = self.mock_notification_send.call_args_list[0][1]
        print(first_call_args)
        second_call_args = self.mock_notification_send.call_args_list[1][1]
        print(second_call_args)

        assert second_call_args['to_addr'] == reg_user.email

    def test_send_claim_registered_email_before_throttle_expires(self):
        reg_user = UserFactory()
        send_claim_registered_email(
            claimer=reg_user,
            unclaimed_user=self.user,
            node=self.project,
        )
        self.mock_notification_send.reset_mock()
        # second call raises error because it was called before throttle period
        with pytest.raises(HTTPError):
            send_claim_registered_email(
                claimer=reg_user,
                unclaimed_user=self.user,
                node=self.project,
            )
        assert not self.mock_notification_send.called

    @mock.patch('website.project.views.contributor.send_claim_registered_email')
    def test_claim_user_post_with_email_already_registered_sends_correct_email(
            self, send_claim_registered_email):
        reg_user = UserFactory()
        payload = {
            'value': reg_user.username,
            'pk': self.user._primary_key
        }
        url = self.project.api_url_for('claim_user_post', uid=self.user._id)
        self.app.post(url, json=payload)
        assert send_claim_registered_email.called

    def test_user_with_removed_unclaimed_url_claiming(self):
        """ Tests that when an unclaimed user is removed from a project, the
        unregistered user object does not retain the token.
        """
        self.project.remove_contributor(self.user, Auth(user=self.referrer))

        assert self.project._primary_key not in self.user.unclaimed_records.keys()

    def test_user_with_claim_url_cannot_claim_twice(self):
        """ Tests that when an unclaimed user is replaced on a project with a
        claimed user, the unregistered user object does not retain the token.
        """
        reg_user = AuthUserFactory()

        self.project.replace_contributor(self.user, reg_user)

        assert self.project._primary_key not in self.user.unclaimed_records.keys()

    def test_claim_user_form_redirects_to_password_confirm_page_if_user_is_logged_in(self):
        reg_user = AuthUserFactory()
        url = self.user.get_claim_url(self.project._primary_key)
        res = self.app.get(url, auth=reg_user.auth)
        assert res.status_code == 302
        res = self.app.get(url, auth=reg_user.auth, follow_redirects=True)
        token = self.user.get_unclaimed_record(self.project._primary_key)['token']
        expected = self.project.web_url_for(
            'claim_user_registered',
            uid=self.user._id,
            token=token,
        )
        assert res.request.path == expected

    @mock.patch('framework.auth.cas.make_response_from_ticket')
    def test_claim_user_when_user_is_registered_with_orcid(self, mock_response_from_ticket):
        # TODO: check in qa url encoding
        token = self.user.get_unclaimed_record(self.project._primary_key)['token']
        url = f'/user/{self.user._id}/{self.project._id}/claim/verify/{token}/'
        # logged out user gets redirected to cas login
        res1 = self.app.get(url)
        assert res1.status_code == 302
        res = self.app.resolve_redirect(self.app.get(url))
        service_url = f'http://localhost{url}'
        expected = cas.get_logout_url(service_url=cas.get_login_url(service_url=service_url))
        assert res1.location == expected

        # user logged in with orcid automatically becomes a contributor
        orcid_user, validated_credentials, cas_resp = generate_external_user_with_resp(url)
        mock_response_from_ticket.return_value = authenticate(
            orcid_user,
            redirect(url)
        )
        orcid_user.set_unusable_password()
        orcid_user.save()

        # The request to OSF with CAS service ticket must not have cookie and/or auth.
        service_ticket = fake.md5()
        url_with_service_ticket = f'{url}?ticket={service_ticket}'
        res = self.app.get(url_with_service_ticket)
        # The response of this request is expected to be a 302 with `Location`.
        # And the redirect URL must equal to the originial service URL
        assert res.status_code == 302
        redirect_url = res.headers['Location']
        assert redirect_url == url
        # The response of this request is expected have the `Set-Cookie` header with OSF cookie.
        # And the cookie must belong to the ORCiD user.
        raw_set_cookie = res.headers['Set-Cookie']
        assert raw_set_cookie
        simple_cookie = SimpleCookie()
        simple_cookie.load(raw_set_cookie)
        cookie_dict = {key: value.value for key, value in simple_cookie.items()}
        osf_cookie = cookie_dict.get(settings.COOKIE_NAME, None)
        assert osf_cookie is not None
        user = OSFUser.from_cookie(osf_cookie)
        assert user._id == orcid_user._id
        # The ORCiD user must be different from the unregistered user created when the contributor was added
        assert user._id != self.user._id

        # Must clear the Flask g context manual and set the OSF cookie to context
        g.current_session = None
        self.app.set_cookie(settings.COOKIE_NAME, osf_cookie)
        res = self.app.resolve_redirect(res)
        assert res.status_code == 302
        assert self.project.is_contributor(orcid_user)
        assert self.project.url in res.headers.get('Location')

    def test_get_valid_form(self):
        url = self.user.get_claim_url(self.project._primary_key)
        res = self.app.get(url, follow_redirects=True)
        assert res.status_code == 200

    def test_invalid_claim_form_raise_400(self):
        uid = self.user._primary_key
        pid = self.project._primary_key
        url = f'/user/{uid}/{pid}/claim/?token=badtoken'
        res = self.app.get(url, follow_redirects=True)
        assert res.status_code == 400

    @mock.patch('osf.models.OSFUser.update_search_nodes')
    def test_posting_to_claim_form_with_valid_data(self, mock_update_search_nodes):
        url = self.user.get_claim_url(self.project._primary_key)
        res = self.app.post(url, data={
            'username': self.user.username,
            'password': 'killerqueen',
            'password2': 'killerqueen'
        })

        assert res.status_code == 302
        location = res.headers.get('Location')
        assert 'login?service=' in location
        assert 'username' in location
        assert 'verification_key' in location
        assert self.project._primary_key in location

        self.user.reload()
        assert self.user.is_registered
        assert self.user.is_active
        assert self.project._primary_key not in self.user.unclaimed_records

    @mock.patch('osf.models.OSFUser.update_search_nodes')
    def test_posting_to_claim_form_removes_all_unclaimed_data(self, mock_update_search_nodes):
        # user has multiple unclaimed records
        p2 = ProjectFactory(creator=self.referrer)
        self.user.add_unclaimed_record(p2, referrer=self.referrer,
                                       given_name=fake.name())
        self.user.save()
        assert len(self.user.unclaimed_records.keys()) > 1  # sanity check
        url = self.user.get_claim_url(self.project._primary_key)
        res = self.app.post(url, data={
            'username': self.given_email,
            'password': 'bohemianrhap',
            'password2': 'bohemianrhap'
        })
        self.user.reload()
        assert self.user.unclaimed_records == {}

    @mock.patch('osf.models.OSFUser.update_search_nodes')
    def test_posting_to_claim_form_sets_fullname_to_given_name(self, mock_update_search_nodes):
        # User is created with a full name
        original_name = fake.name()
        unreg = UnregUserFactory(fullname=original_name)
        # User invited with a different name
        different_name = fake.name()
        new_user = self.project.add_unregistered_contributor(
            email=unreg.username,
            fullname=different_name,
            auth=Auth(self.project.creator),
        )
        self.project.save()
        # Goes to claim url
        claim_url = new_user.get_claim_url(self.project._id)
        self.app.post(claim_url, data={
            'username': unreg.username,
            'password': 'killerqueen',
            'password2': 'killerqueen'
        })
        unreg.reload()
        # Full name was set correctly
        assert unreg.fullname == different_name
        # CSL names were set correctly
        parsed_name = impute_names_model(different_name)
        assert unreg.given_name == parsed_name['given_name']
        assert unreg.family_name == parsed_name['family_name']

    def test_claim_user_post_returns_fullname(self):
        url = f'/api/v1/user/{self.user._primary_key}/{self.project._primary_key}/claim/email/'
        res = self.app.post(
            url,
            auth=self.referrer.auth,
            json={
                'value': self.given_email,
                'pk': self.user._primary_key
            },
        )
        assert res.json['fullname'] == self.given_name
        assert self.mock_notification_send.called

    def test_claim_user_post_if_email_is_different_from_given_email(self):
        email = fake_email()  # email that is different from the one the referrer gave
        url = f'/api/v1/user/{self.user._primary_key}/{self.project._primary_key}/claim/email/'
        self.app.post(url, json={'value': email, 'pk': self.user._primary_key} )
        assert self.mock_notification_send.called
        assert self.mock_notification_send.call_count == 2
        call_to_invited = self.mock_notification_send.mock_calls[0]
        call_to_invited.assert_called_with(to_addr=email)
        call_to_referrer = self.mock_notification_send.mock_calls[1]
        call_to_referrer.assert_called_with(to_addr=self.given_email)

    def test_claim_url_with_bad_token_returns_400(self):
        url = self.project.web_url_for(
            'claim_user_registered',
            uid=self.user._id,
            token='badtoken',
        )
        res = self.app.get(url, auth=self.referrer.auth)
        assert res.status_code == 400

    def test_cannot_claim_user_with_user_who_is_already_contributor(self):
        # user who is already a contirbutor to the project
        contrib = AuthUserFactory()
        self.project.add_contributor(contrib, auth=Auth(self.project.creator))
        self.project.save()
        # Claiming user goes to claim url, but contrib is already logged in
        url = self.user.get_claim_url(self.project._primary_key)
        res = self.app.get(
            url,
            auth=contrib.auth, follow_redirects=True)
        # Response is a 400
        assert res.status_code == 400

    def test_claim_user_with_project_id_adds_corresponding_claimed_tag_to_user(self):
        assert OsfClaimedTags.Osf.value not in self.user.system_tags
        url = self.user.get_claim_url(self.project_with_source_tag._primary_key)
        res = self.app.post(url, data={
            'username': self.user.username,
            'password': 'killerqueen',
            'password2': 'killerqueen'
        })

        assert res.status_code == 302
        self.user.reload()
        assert OsfClaimedTags.Osf.value in self.user.system_tags

    def test_claim_user_with_preprint_id_adds_corresponding_claimed_tag_to_user(self):
        assert provider_claimed_tag(self.preprint_with_source_tag.provider._id, 'preprint') not in self.user.system_tags
        url = self.user.get_claim_url(self.preprint_with_source_tag._primary_key)
        res = self.app.post(url, data={
            'username': self.user.username,
            'password': 'killerqueen',
            'password2': 'killerqueen'
        })

        assert res.status_code == 302
        self.user.reload()
        assert provider_claimed_tag(self.preprint_with_source_tag.provider._id, 'preprint') in self.user.system_tags
