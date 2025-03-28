from unittest import mock
import pytest
import datetime
from django.utils import timezone
from api.base.settings.defaults import API_BASE
from osf.utils import permissions
from osf.models import Registration, NodeLicense
from framework.auth import Auth
from website.project.signals import contributor_added
from api_tests.utils import disconnected_from_listeners
from api.registrations.serializers import RegistrationSerializer, RegistrationDetailSerializer
from osf_tests.factories import (
    ProjectFactory,
    NodeFactory,
    RegistrationFactory,
    RegistrationApprovalFactory,
    AuthUserFactory,
    UnregUserFactory,
    OSFGroupFactory,
    InstitutionFactory,
)


class TestRegistrationUpdateTestCase:

    @pytest.fixture()
    def read_only_contributor(self):
        return AuthUserFactory()

    @pytest.fixture()
    def read_write_contributor(self):
        return AuthUserFactory()

    @pytest.fixture()
    def registration_approval(self, user):
        return RegistrationApprovalFactory(
            state='unapproved', approve=False, user=user)

    @pytest.fixture()
    def unapproved_registration(self, registration_approval):
        return Registration.objects.get(
            registration_approval=registration_approval)

    @pytest.fixture()
    def unapproved_url(self, unapproved_registration):
        return '/{}registrations/{}/'.format(
            API_BASE, unapproved_registration._id)

    @pytest.fixture()
    def public_project(self, user):
        return ProjectFactory(
            title='Public Project',
            is_public=True,
            creator=user)

    @pytest.fixture()
    def private_project(self, user):
        return ProjectFactory(title='Private Project', creator=user)

    @pytest.fixture()
    def public_registration(self, user, public_project):
        return RegistrationFactory(
            project=public_project,
            creator=user,
            is_public=True)

    @pytest.fixture()
    def private_registration(
            self, user, private_project, read_only_contributor, read_write_contributor):
        private_registration = RegistrationFactory(
            project=private_project, creator=user)
        private_registration.add_contributor(
            read_only_contributor, permissions=permissions.READ)
        private_registration.add_contributor(
            read_write_contributor, permissions=permissions.WRITE)
        private_registration.save()
        return private_registration

    @pytest.fixture()
    def public_url(self, public_registration):
        return f'/{API_BASE}registrations/{public_registration._id}/'

    @pytest.fixture()
    def private_url(self, private_registration):
        return '/{}registrations/{}/'.format(
            API_BASE, private_registration._id)

    @pytest.fixture()
    def attributes(self):
        return {'public': True}

    @pytest.fixture()
    def institution_one(self):
        return InstitutionFactory()

    @pytest.fixture()
    def make_payload(self, private_registration, attributes):
        def payload(
                id=private_registration._id,
                type='registrations',
                attributes=attributes
        ):
            return {
                'data': {
                    'id': id,
                    'type': type,
                    'attributes': attributes
                }
            }
        return payload

    @pytest.fixture()
    def license_cc0(self):
        return NodeLicense.objects.filter(name='CC0 1.0 Universal').first()


@pytest.mark.django_db
@pytest.mark.enable_implicit_clean
class TestRegistrationUpdate(TestRegistrationUpdateTestCase):
    def test_update_registration(
            self, app, user, read_only_contributor,
            read_write_contributor, public_registration,
            public_url, private_url, make_payload, public_project):

        private_registration_payload = make_payload()
        non_contributor = AuthUserFactory()

    #   test_update_private_registration_logged_out
        res = app.put_json_api(
            private_url,
            private_registration_payload,
            expect_errors=True)
        assert res.status_code == 401

    #   test_update_private_registration_logged_in_admin
        res = app.put_json_api(
            private_url,
            private_registration_payload,
            auth=user.auth)
        assert res.status_code == 200
        assert res.json['data']['attributes']['public'] is True

    #   test_update_private_registration_logged_in_read_only_contributor
        res = app.put_json_api(
            private_url,
            private_registration_payload,
            auth=read_only_contributor.auth,
            expect_errors=True)
        assert res.status_code == 403

    #   test_update_private_registration_logged_in_read_write_contributor
        res = app.put_json_api(
            private_url,
            private_registration_payload,
            auth=read_write_contributor.auth,
            expect_errors=True)
        assert res.status_code == 403

    #   test_update_public_registration_to_private
        public_to_private_payload = make_payload(
            id=public_registration._id, attributes={'public': False})

        res = app.put_json_api(
            public_url,
            public_to_private_payload,
            auth=user.auth,
            expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Registrations can only be turned from private to public.'

        res = app.put_json_api(
            public_url,
            public_to_private_payload,
            auth=non_contributor.auth,
            expect_errors=True)
        assert res.status_code == 403
        assert res.json['errors'][0]['detail'] == 'You do not have permission to perform this action.'

    #   test_osf_group_member_write_cannot_update_registration
        group_mem = AuthUserFactory()
        group = OSFGroupFactory(creator=group_mem)
        public_project.add_osf_group(group, permissions.WRITE)
        res = app.put_json_api(
            public_url,
            public_to_private_payload,
            auth=group_mem.auth,
            expect_errors=True)
        assert res.status_code == 403

    #   test_osf_group_member_admin_cannot_update_registration
        public_project.remove_osf_group(group)
        public_project.add_osf_group(group, permissions.ADMIN)
        res = app.put_json_api(
            public_url,
            public_to_private_payload,
            auth=group_mem.auth,
            expect_errors=True)
        assert res.status_code == 403

    def test_fields(
            self, app, user, public_registration,
            private_registration, public_url, institution_one,
            private_url, make_payload, license_cc0):

        #   test_field_has_invalid_value
        invalid_public_payload = make_payload(
            id=public_registration._id,
            attributes={'public': 'Dr.Strange'})

        res = app.put_json_api(
            public_url,
            invalid_public_payload,
            auth=user.auth,
            expect_errors=True
        )
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Must be a valid boolean.'

        invalid_public_payload = make_payload(
            id=public_registration._id,
            attributes={'category': 'data visualization'})

        res = app.put_json_api(
            public_url,
            invalid_public_payload,
            auth=user.auth,
            expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == '"data visualization" is not a valid choice.'

    #   test_some_registration_fields_are_editable
        user.add_or_update_affiliated_institution(institution_one)
        year = '2009'
        copyright_holders = ['Grapes McGee']
        description = 'New description'
        tags = ['hello', 'hi']
        custom_citation = 'This is my custom citation. Grapes McGee.'
        article_doi = '10.123/456/789'

        attribute_list = {
            'public': True,
            'category': 'instrumentation',
            'title': 'New title',
            'description': description,
            'tags': tags,
            'custom_citation': custom_citation,
            'node_license': {
                'year': year,
                'copyright_holders': copyright_holders
            },
            'article_doi': '10.123/456/789'
        }
        verbose_private_payload = make_payload(attributes=attribute_list)
        verbose_private_payload['data']['relationships'] = {
            'license': {
                'data': {
                    'type': 'licenses',
                    'id': license_cc0._id
                }
            },
            'affiliated_institutions': {
                'data': [
                    {'type': 'institutions', 'id': institution_one._id}
                ]
            }
        }
        res = app.put_json_api(
            private_url,
            verbose_private_payload,
            auth=user.auth)
        assert res.status_code == 200
        assert res.json['data']['attributes']['public'] is True
        assert res.json['data']['attributes']['category'] == 'instrumentation'
        assert res.json['data']['attributes']['description'] == description
        assert res.json['data']['attributes']['tags'] == tags
        assert res.json['data']['attributes']['title'] == 'New title'
        assert res.json['data']['attributes']['node_license']['copyright_holders'] == copyright_holders
        assert res.json['data']['attributes']['node_license']['year'] == year
        assert res.json['data']['attributes']['custom_citation'] == custom_citation
        assert res.json['data']['attributes']['article_doi'] == article_doi

        institution_links = res.json['data']['relationships']['affiliated_institutions']['links']
        assert '/{}registrations/{}/institutions/'.format(
            API_BASE, private_registration._id) in institution_links['related']['href']
        assert '/{}registrations/{}/relationships/institutions/'.format(
            API_BASE, private_registration._id) in institution_links['self']['href']

    #   test_can_unset_certain_registration_fields
        attribute_list = {
            'public': True,
            'category': '',
            'title': 'New title',
            'description': '',
            'tags': [],
            'custom_citation': '',
            'node_license': {
                'year': '',
                'copyright_holders': []
            }
        }
        verbose_private_payload = make_payload(attributes=attribute_list)

        res = app.put_json_api(
            private_url,
            verbose_private_payload,
            auth=user.auth)
        assert res.status_code == 200
        assert res.json['data']['attributes']['public'] is True
        assert res.json['data']['attributes']['category'] == ''
        assert res.json['data']['attributes']['description'] == ''
        assert res.json['data']['attributes']['tags'] == []
        assert res.json['data']['attributes']['title'] == 'New title'
        assert res.json['data']['attributes']['node_license']['copyright_holders'] == []
        assert res.json['data']['attributes']['node_license']['year'] == ''
        assert res.json['data']['attributes']['custom_citation'] == ''

    #   test_type_field_must_match
        node_type_payload = make_payload(type='node')

        res = app.put_json_api(
            private_url,
            node_type_payload,
            auth=user.auth,
            expect_errors=True)
        assert res.status_code == 409

    #   test_id_field_must_match
        mismatch_id_payload = make_payload(id='12345')

        res = app.put_json_api(
            private_url,
            mismatch_id_payload,
            auth=user.auth,
            expect_errors=True)
        assert res.status_code == 409

    #   test_invalid_doi
        bad_doi_payload = make_payload(attributes={'article_doi': 'blah'})
        res = app.put_json_api(
            private_url,
            bad_doi_payload,
            auth=user.auth,
            expect_errors=True)
        assert res.status_code == 400

    def test_turning_private_registrations_public(
            self, app, user, make_payload):
        private_project = ProjectFactory(creator=user, is_public=False)
        private_registration = RegistrationFactory(
            project=private_project, creator=user, is_public=False)

        private_to_public_payload = make_payload(id=private_registration._id)

        url = f'/{API_BASE}registrations/{private_registration._id}/'
        res = app.put_json_api(url, private_to_public_payload, auth=user.auth)
        assert res.json['data']['attributes']['public'] is True
        private_registration.reload()
        assert private_registration.is_public

    def test_registration_fields_are_read_only(self):
        writeable_fields = [
            'title',
            'type',
            'public',
            'draft_registration',
            'registration_choice',
            'lift_embargo',
            'children',
            'tags',
            'description',
            'node_license',
            'license',
            'affiliated_institutions',
            'article_doi',
            'custom_citation',
            'category',
            'provider_specific_metadata',
        ]
        for field in RegistrationSerializer._declared_fields:
            reg_field = RegistrationSerializer._declared_fields[field]
            if field not in writeable_fields:
                assert getattr(reg_field, 'read_only', False) is True

    def test_registration_detail_fields_are_read_only(self):
        writeable_fields = [
            'title',
            'type',
            'public',
            'draft_registration',
            'registration_choice',
            'lift_embargo',
            'children',
            'pending_withdrawal',
            'withdrawal_justification',
            'tags',
            'description',
            'node_license',
            'license',
            'affiliated_institutions',
            'article_doi',
            'custom_citation',
            'category',
            'provider_specific_metadata',
        ]
        for field in RegistrationDetailSerializer._declared_fields:
            reg_field = RegistrationSerializer._declared_fields[field]
            if field not in writeable_fields:
                assert getattr(reg_field, 'read_only', False) is True

    def test_user_cannot_delete_registration(self, app, user, private_url):
        res = app.delete_json_api(
            private_url,
            expect_errors=True,
            auth=user.auth)
        assert res.status_code == 405

    def test_make_public_unapproved_registration_raises_error(
            self, app, user, unapproved_registration, unapproved_url, make_payload):
        attribute_list = {
            'public': True,
        }
        unapproved_registration_payload = make_payload(
            id=unapproved_registration._id, attributes=attribute_list)

        res = app.put_json_api(
            unapproved_url,
            unapproved_registration_payload,
            auth=user.auth,
            expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'An unapproved registration cannot be made public.'

    def test_read_write_contributor_can_edit_writeable_fields(
            self, app, read_write_contributor, private_registration,
            private_url, make_payload, institution_one):

        #  test_read_write_contributor_cannot_update_custom_citation
        payload = make_payload(
            id=private_registration._id,
            attributes={'custom_citation': 'This is a custom citation yay'}
        )
        res = app.put_json_api(private_url, payload, auth=read_write_contributor.auth, expect_errors=True)
        assert res.status_code == 403

        #  test_read_write_contributor_cannot_update_description
        payload = make_payload(
            id=private_registration._id,
            attributes={'description': 'Updated description'}
        )
        res = app.put_json_api(private_url, payload, auth=read_write_contributor.auth)
        assert res.status_code == 200

        payload = make_payload(
            id=private_registration._id,
            attributes={'title': 'Updated title'}
        )
        res = app.put_json_api(private_url, payload, auth=read_write_contributor.auth)
        assert res.status_code == 200

        #  test_read_write_contributor_cannot_update_category
        payload = make_payload(
            id=private_registration._id,
            attributes={'category': 'instrumentation'}
        )
        res = app.put_json_api(private_url, payload, auth=read_write_contributor.auth)
        assert res.status_code == 200

        #  test_read_write_contributor_cannot_update_article_doi
        payload = make_payload(
            id=private_registration._id,
            attributes={'article_doi': '10.123/456/789'}
        )
        res = app.put_json_api(private_url, payload, auth=read_write_contributor.auth)
        assert res.status_code == 200

        #  test_read_write_contributor_cannot_update_affiliated_institution
        payload = make_payload(
            id=private_registration._id,
        )
        payload['relationships'] = {
            'affiliated_institutions': {
                'data': [
                    {'type': 'institutions', 'id': institution_one._id}
                ]
            }
        }
        del payload['data']['attributes']  # just check permissions on institutions relationship
        res = app.put_json_api(private_url, payload, auth=read_write_contributor.auth)
        assert res.status_code == 200


@pytest.mark.django_db
class TestRegistrationWithdrawal(TestRegistrationUpdateTestCase):

    @pytest.fixture
    def public_payload(self, public_registration, make_payload):
        return make_payload(
            id=public_registration._id,
            attributes={'pending_withdrawal': True, 'withdrawal_justification': 'Not enough oopmh.'}
        )

    def test_initiate_withdraw_registration_fails(
            self, app, user, read_write_contributor, public_registration, make_payload,
            private_registration, public_url, private_url, public_project, public_payload):
        # test set pending_withdrawal with no auth
        res = app.put_json_api(public_url, public_payload, expect_errors=True)
        assert res.status_code == 401

        # test set pending_withdrawal from a read write contrib
        public_registration.add_contributor(read_write_contributor, permissions=permissions.WRITE)
        public_registration.save()
        res = app.put_json_api(public_url, public_payload, auth=read_write_contributor.auth, expect_errors=True)
        assert res.status_code == 403

        # test set pending_withdrawal private registration fails
        payload_private = make_payload(
            id=private_registration._id,
            attributes={'pending_withdrawal': True, 'withdrawal_justification': 'fine whatever'}
        )
        res = app.put_json_api(private_url, payload_private, auth=user.auth, expect_errors=True)
        assert res.status_code == 400

        # test set pending_withdrawal for component fails
        project = ProjectFactory(is_public=True, creator=user)
        NodeFactory(is_public=True, creator=user, parent=project)
        registration_with_comp = RegistrationFactory(is_public=True, project=project)
        registration_comp = registration_with_comp._nodes.first()
        payload_component = make_payload(
            id=registration_comp._id,
            attributes={'pending_withdrawal': True}
        )
        url = f'/{API_BASE}registrations/{registration_comp._id}/'
        res = app.put_json_api(url, payload_component, auth=user.auth, expect_errors=True)
        assert res.status_code == 400

        # setting pending_withdrawal to false fails
        public_payload['data']['attributes'] = {'pending_withdrawal': False}
        res = app.put_json_api(public_url, public_payload, auth=user.auth, expect_errors=True)
        assert res.status_code == 400

        # test set pending_withdrawal with just withdrawal_justification key
        public_payload['data']['attributes'] = {'withdrawal_justification': 'Not enough oopmh.'}
        res = app.put_json_api(public_url, public_payload, auth=user.auth, expect_errors=True)
        assert res.status_code == 400

        # set pending_withdrawal on a registration already pending withdrawal fails
        public_registration._initiate_retraction(user)
        res = app.put_json_api(public_url, public_payload, auth=user.auth, expect_errors=True)
        assert res.status_code == 400

    @mock.patch('website.mails.send_mail')
    def test_initiate_withdrawal_success(self, mock_send_mail, app, user, public_registration, public_url, public_payload):
        res = app.put_json_api(public_url, public_payload, auth=user.auth)
        assert res.status_code == 200
        assert res.json['data']['attributes']['pending_withdrawal'] is True
        public_registration.refresh_from_db()
        assert public_registration.is_pending_retraction
        assert public_registration.registered_from.logs.first().action == 'retraction_initiated'
        assert mock_send_mail.called

    def test_initiate_withdrawal_with_embargo_ends_embargo(
            self, app, user, public_project, public_registration, public_url, public_payload):
        public_registration.embargo_registration(
            user,
            (timezone.now() + datetime.timedelta(days=10)),
            for_existing_registration=True
        )
        public_registration.save()
        assert public_registration.is_pending_embargo

        approval_token = public_registration.embargo.approval_state[user._id]['approval_token']
        public_registration.embargo.approve(user, approval_token)
        assert public_registration.embargo_end_date

        res = app.put_json_api(public_url, public_payload, auth=user.auth)
        assert res.status_code == 200
        assert res.json['data']['attributes']['pending_withdrawal'] is True
        public_registration.reload()
        assert public_registration.is_pending_retraction
        assert not public_registration.is_pending_embargo

    @mock.patch('website.mails.send_mail')
    def test_withdraw_request_does_not_send_email_to_unregistered_admins(
            self, mock_send_mail, app, user, public_registration, public_url, public_payload):
        unreg = UnregUserFactory()
        with disconnected_from_listeners(contributor_added):
            public_registration.add_unregistered_contributor(
                unreg.fullname,
                unreg.email,
                auth=Auth(user),
                permissions=permissions.ADMIN,
                existing_user=unreg,
                save=True
            )

        res = app.put_json_api(public_url, public_payload, auth=user.auth)
        assert res.status_code == 200

        # Only the creator gets an email; the unreg user does not get emailed
        assert public_registration._contributors.count() == 2
        assert mock_send_mail.call_count == 1
