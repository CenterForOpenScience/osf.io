import pytest
from waffle.testutils import override_switch
from osf import features
from api.providers.workflows import Workflows
from osf.models import NotificationType
from osf.models import schema_response  # import module for mocking purposes
from osf.utils.workflows import ApprovalStates
from osf_tests.factories import AuthUserFactory, ProjectFactory, RegistrationFactory, RegistrationProviderFactory
from osf_tests.utils import get_default_test_schema
from tests.utils import get_mailhog_messages, delete_mailhog_messages, capture_notifications, assert_emails

# See osf_tests.utils.default_test_schema for block types and valid answers
INITIAL_SCHEMA_RESPONSES = {
    'q1': 'Some answer',
    'q2': 'Some even longer answer',
    'q3': 'A',
    'q4': ['D', 'G'],
    'q5': '',
    'q6': []
}

DEFAULT_SCHEMA_RESPONSE_VALUES = {
    'q1': '', 'q2': '', 'q3': '', 'q4': [], 'q5': '', 'q6': []
}

@pytest.fixture
def admin_user():
    return AuthUserFactory()


@pytest.fixture
def schema():
    return get_default_test_schema()


@pytest.fixture
def registration(schema, admin_user):
    registration = RegistrationFactory(schema=schema, creator=admin_user)
    registration.schema_responses.clear()  # so we can use `create_initial_response` without validation
    return registration


@pytest.fixture
def alternate_user(registration):
    user = AuthUserFactory()
    registration.add_contributor(user, 'read')
    return user


@pytest.fixture
def nested_registration(registration, schema):
    project = ProjectFactory(parent=registration.registered_from)
    project.save()
    return RegistrationFactory(project=project, parent=registration, schema=schema)


@pytest.fixture
def nested_contributor(nested_registration):
    return nested_registration.creator


@pytest.fixture
def notification_recipients(admin_user, alternate_user, nested_contributor):
    return {user.username for user in [admin_user, alternate_user, nested_contributor]}


@pytest.fixture
def initial_response(registration):
    response = schema_response.SchemaResponse.create_initial_response(
        initiator=registration.creator,
        parent=registration
    )
    response.approvals_state_machine.set_state(ApprovalStates.APPROVED)
    response.save()
    for block in response.response_blocks.all():
        block.response = INITIAL_SCHEMA_RESPONSES[block.schema_key]
        block.save()

    return response


@pytest.fixture
def revised_response(initial_response):
    revised_response = schema_response.SchemaResponse.create_from_previous_response(
        previous_response=initial_response,
        initiator=initial_response.initiator
    )
    return revised_response


@pytest.mark.enable_bookmark_creation
@pytest.mark.django_db
class TestCreateSchemaResponse():

    @override_switch(features.ENABLE_MAILHOG, active=True)
    def test_create_from_previous_response_notification(
            self, initial_response, admin_user, notification_recipients):
        delete_mailhog_messages()
        with capture_notifications(passthrough=True) as notifications:
            schema_response.SchemaResponse.create_from_previous_response(
                previous_response=initial_response,
                initiator=admin_user
            )
        assert len(notifications['emits']) == len(notification_recipients)
        assert all(notification['type'] == NotificationType.Type.NODE_SCHEMA_RESPONSE_INITIATED for notification in notifications['emits'])
        assert all(notification['kwargs']['user'].username in notification_recipients for notification in notifications['emits'])
        massages = get_mailhog_messages()
        assert massages['count'] == len(notifications['emails'])
        assert_emails(massages, notifications)

        delete_mailhog_messages()


@pytest.mark.django_db
class TestUnmoderatedSchemaResponseApprovalFlows():

    @override_switch(features.ENABLE_MAILHOG, active=True)
    def test_submit_response_notification(
            self, revised_response, admin_user, notification_recipients):
        revised_response.approvals_state_machine.set_state(ApprovalStates.IN_PROGRESS)
        revised_response.update_responses({'q1': 'must change one response or can\'t submit'})
        revised_response.revision_justification = 'has for valid revision_justification for submission'
        revised_response.save()
        delete_mailhog_messages()
        with capture_notifications(passthrough=True) as notifications:
            revised_response.submit(user=admin_user, required_approvers=[admin_user])
        assert len(notifications['emits']) == 3
        assert any(notification['type'] == NotificationType.Type.NODE_SCHEMA_RESPONSE_SUBMITTED for notification in notifications['emits'])
        massages = get_mailhog_messages()
        assert massages['count'] == len(notifications['emails'])
        assert_emails(massages, notifications)

        delete_mailhog_messages()

    @override_switch(features.ENABLE_MAILHOG, active=True)
    def test_approve_response_notification(
            self, revised_response, admin_user, alternate_user, notification_recipients):
        revised_response.approvals_state_machine.set_state(ApprovalStates.UNAPPROVED)
        revised_response.save()
        revised_response.pending_approvers.add(admin_user, alternate_user)
        delete_mailhog_messages()
        with capture_notifications(passthrough=True) as notifications:
            revised_response.approve(user=admin_user)
        assert notifications == {'emails': [], 'emits': []}  # Should only send email on final approval
        with capture_notifications(passthrough=True) as notifications:
            revised_response.approve(user=alternate_user)
        assert len(notifications['emits']) == 3
        assert all(notification['type'] == NotificationType.Type.NODE_SCHEMA_RESPONSE_APPROVED for notification in notifications['emits'])
        massages = get_mailhog_messages()
        assert massages['count'] == len(notifications['emails'])
        assert_emails(massages, notifications)

        delete_mailhog_messages()

    @override_switch(features.ENABLE_MAILHOG, active=True)
    def test_reject_response_notification(
            self, revised_response, admin_user, notification_recipients):
        revised_response.approvals_state_machine.set_state(ApprovalStates.UNAPPROVED)
        revised_response.save()
        revised_response.pending_approvers.add(admin_user)
        delete_mailhog_messages()
        with capture_notifications(passthrough=True) as notifications:
            revised_response.reject(user=admin_user)
        assert len(notifications['emits']) == 3
        assert all(notification['type'] == NotificationType.Type.NODE_SCHEMA_RESPONSE_REJECTED for notification in notifications['emits'])
        massages = get_mailhog_messages()
        assert massages['count'] == len(notifications['emails'])
        assert_emails(massages, notifications)

        delete_mailhog_messages()


@pytest.mark.django_db
class TestModeratedSchemaResponseApprovalFlows():

    @pytest.fixture
    def provider(self):
        provider = RegistrationProviderFactory()
        provider.update_group_permissions()
        provider.reviews_workflow = Workflows.PRE_MODERATION.value
        provider.save()
        return provider

    @pytest.fixture
    def moderator(self, provider):
        moderator = AuthUserFactory()
        provider.add_to_group(moderator, 'moderator')
        return moderator

    @pytest.fixture
    def registration(self, registration, provider):
        registration.provider = provider
        registration.save()
        return registration

    @override_switch(features.ENABLE_MAILHOG, active=True)
    def test_accept_notification_sent_on_admin_approval(self, revised_response, admin_user, moderator):
        revised_response.approvals_state_machine.set_state(ApprovalStates.UNAPPROVED)
        revised_response.save()
        revised_response.pending_approvers.add(admin_user)
        delete_mailhog_messages()
        with capture_notifications(passthrough=True) as notifications:
            revised_response.approve(user=admin_user)
        assert len(notifications['emits']) == 3
        assert notifications['emits'][0]['kwargs']['user'] == moderator
        assert notifications['emits'][0]['type'] == NotificationType.Type.PROVIDER_NEW_PENDING_SUBMISSIONS
        assert notifications['emits'][1]['kwargs']['user'] == moderator
        assert notifications['emits'][1]['type'] == NotificationType.Type.PROVIDER_NEW_PENDING_SUBMISSIONS
        assert notifications['emits'][2]['kwargs']['user'] == admin_user
        assert notifications['emits'][2]['type'] == NotificationType.Type.NODE_SCHEMA_RESPONSE_APPROVED
        massages = get_mailhog_messages()
        assert massages['count'] == len(notifications['emails'])
        assert_emails(massages, notifications)

        delete_mailhog_messages()

    @override_switch(features.ENABLE_MAILHOG, active=True)
    def test_moderators_notified_on_admin_approval(self, revised_response, admin_user, moderator):
        revised_response.approvals_state_machine.set_state(ApprovalStates.UNAPPROVED)
        revised_response.save()
        revised_response.pending_approvers.add(admin_user)
        delete_mailhog_messages()
        with capture_notifications(passthrough=True) as notifications:
            revised_response.approve(user=admin_user)
        assert len(notifications['emits']) == 3
        assert notifications['emits'][0]['kwargs']['user'] == moderator
        assert notifications['emits'][0]['type'] == NotificationType.Type.PROVIDER_NEW_PENDING_SUBMISSIONS
        assert notifications['emits'][1]['kwargs']['user'] == moderator
        assert notifications['emits'][1]['type'] == NotificationType.Type.PROVIDER_NEW_PENDING_SUBMISSIONS
        assert notifications['emits'][2]['kwargs']['user'] == admin_user
        assert notifications['emits'][2]['type'] == NotificationType.Type.NODE_SCHEMA_RESPONSE_APPROVED
        massages = get_mailhog_messages()
        assert massages['count'] == len(notifications['emails'])
        assert_emails(massages, notifications)

        delete_mailhog_messages()

    @override_switch(features.ENABLE_MAILHOG, active=True)
    def test_moderator_accept_notification(
            self, revised_response, moderator, notification_recipients):
        revised_response.approvals_state_machine.set_state(ApprovalStates.PENDING_MODERATION)
        revised_response.save()
        delete_mailhog_messages()
        with capture_notifications(passthrough=True) as notifications:
            revised_response.accept(user=moderator)
        assert len(notifications['emits']) == 3
        assert all(notification['type'] == NotificationType.Type.NODE_SCHEMA_RESPONSE_APPROVED for notification in notifications['emits'])
        massages = get_mailhog_messages()
        assert massages['count'] == len(notifications['emails'])
        assert_emails(massages, notifications)

        delete_mailhog_messages()

    @override_switch(features.ENABLE_MAILHOG, active=True)
    def test_moderator_reject_notification(
            self, revised_response, moderator, notification_recipients):
        revised_response.approvals_state_machine.set_state(ApprovalStates.PENDING_MODERATION)
        revised_response.save()
        delete_mailhog_messages()
        with capture_notifications(passthrough=True) as notifications:
            revised_response.reject(user=moderator)
        assert len(notifications['emits']) == 3
        assert all(notification['type'] == NotificationType.Type.NODE_SCHEMA_RESPONSE_REJECTED for notification in notifications['emits'])
        massages = get_mailhog_messages()
        assert massages['count'] == len(notifications['emails'])
        assert_emails(massages, notifications)

        delete_mailhog_messages()
