from unittest import mock
import pytest

from api.providers.workflows import Workflows
from framework.exceptions import PermissionsError
from osf.exceptions import PreviousSchemaResponseError, SchemaResponseStateError, SchemaResponseUpdateError
from osf.models import RegistrationSchema, RegistrationSchemaBlock, SchemaResponseBlock
from osf.models import schema_response  # import module for mocking purposes
from osf.utils.workflows import ApprovalStates, SchemaResponseTriggers
from osf_tests.factories import AuthUserFactory, ProjectFactory, RegistrationFactory, RegistrationProviderFactory
from osf_tests.utils import get_default_test_schema, assert_notification_correctness, _ensure_subscriptions

from website.mails import mails
from website.notifications import emails

from transitions import MachineError

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

    def test_create_initial_response_sets_attributes(self, registration, schema):
        response = schema_response.SchemaResponse.create_initial_response(
            initiator=registration.creator,
            parent=registration,
            schema=schema
        )

        assert response.parent == registration
        assert response in registration.schema_responses.all()
        assert response.schema == schema
        assert response.initiator == registration.creator
        assert not response.submitted_timestamp

    def test_create_initial_response_uses_parent_schema_if_none_provided(self, registration):
        response = schema_response.SchemaResponse.create_initial_response(
            initiator=registration.creator,
            parent=registration
        )

        assert response.schema == registration.registration_schema

    def test_create_initial_response_assigns_response_blocks_and_source_revision(
            self, registration, schema):
        assert not SchemaResponseBlock.objects.exists()
        response = schema_response.SchemaResponse.create_initial_response(
            initiator=registration.creator, parent=registration,
        )
        # No previous SchemaResponseBlocks means all SchemaResponseBlocks in existence
        # were created by the create_initial_response call
        created_response_blocks = set(SchemaResponseBlock.objects.all())

        # Confirm that the all of the created blocks have the created response as their
        # source revision and that response_blocks has all of the created blocks
        assert created_response_blocks == set(response.updated_response_blocks.all())
        assert created_response_blocks == set(response.response_blocks.all())

    def test_create_initial_response_assigns_default_values(self, registration):
        response = schema_response.SchemaResponse.create_initial_response(
            initiator=registration.creator, parent=registration
        )

        for block in response.response_blocks.all():
            assert block.response == DEFAULT_SCHEMA_RESPONSE_VALUES[block.schema_key]

    def test_create_initial_response_does_not_notify(self, registration, admin_user):
        with mock.patch.object(schema_response.mails, 'send_mail', autospec=True) as mock_send:
            schema_response.SchemaResponse.create_initial_response(
                parent=registration, initiator=admin_user
            )
        assert not mock_send.called

    def test_create_initial_response_fails_if_no_schema_and_no_parent_schema(self, registration):
        registration.registered_schema.clear()
        registration.save()
        with pytest.raises(ValueError):
            schema_response.SchemaResponse.create_initial_response(
                initiator=registration.creator,
                parent=registration
            )

    def test_create_initial_response_fails_if_schema_and_parent_schema_mismatch(self, registration):
        alt_schema = RegistrationSchema.objects.exclude(
            id=registration.registration_schema.id
        ).first()
        with pytest.raises(ValueError):
            schema_response.SchemaResponse.create_initial_response(
                initiator=registration.creator,
                parent=registration,
                schema=alt_schema
            )

    def test_create_initial_response_creates_blocks_for_each_schema_question(self, registration):
        assert not SchemaResponseBlock.objects.exists()
        schema = registration.registration_schema
        schema_response.SchemaResponse.create_initial_response(
            initiator=registration.creator,
            parent=registration,
            schema=schema
        )
        # No previous SchemaResponseBlocks means all SchemaResponseBlocks in existence
        # were created by the create_initial_response call
        created_response_blocks = SchemaResponseBlock.objects.all()

        # Confirm that exactly one block was created for each registration_response_key on the schema
        schema_input_blocks = RegistrationSchemaBlock.objects.filter(
            schema=schema, registration_response_key__isnull=False)
        assert schema_input_blocks.count() == created_response_blocks.count()
        for key in schema_input_blocks.values_list('registration_response_key', flat=True):
            assert created_response_blocks.filter(schema_key=key).exists()

    def test_cannot_create_initial_response_twice(self, registration):
        schema_response.SchemaResponse.create_initial_response(
            initiator=registration.creator,
            parent=registration,
        )

        with pytest.raises(PreviousSchemaResponseError):
            schema_response.SchemaResponse.create_initial_response(
                initiator=registration.creator,
                parent=registration,
            )

    def test_create_initial_response_for_different_parent(self, registration):
        schema = registration.registration_schema
        first_response = schema_response.SchemaResponse.create_initial_response(
            initiator=registration.creator,
            parent=registration,
        )

        alternate_registration = RegistrationFactory(schema=schema)
        alternate_registration.schema_responses.clear()  # so we can use `create_initial_response` without validation

        alternate_registration_response = schema_response.SchemaResponse.create_initial_response(
            initiator=alternate_registration.creator,
            parent=alternate_registration,
        )

        # Confirm that a response block was created for each input block
        schema_input_blocks = RegistrationSchemaBlock.objects.filter(
            schema=schema, registration_response_key__isnull=False)
        assert (
            alternate_registration_response.updated_response_blocks.count()
            == schema_input_blocks.count()
        )
        # Confirm that all of the response_blocks for these response
        # have these response as their source
        assert (
            set(alternate_registration_response.updated_response_blocks.all())
            == set(alternate_registration_response.response_blocks.all())
        )

        # There should be no overlap between the response blocks for the
        # two sets of "initial" response
        assert not first_response.response_blocks.all().intersection(
            alternate_registration_response.response_blocks.all()
        ).exists()

    def test_create_from_previous_response(self, registration, initial_response):
        revised_response = schema_response.SchemaResponse.create_from_previous_response(
            initiator=registration.creator,
            previous_response=initial_response,
            justification='Leeeeerooooy Jeeeenkiiiinns'
        )

        assert revised_response.initiator == registration.creator
        assert revised_response.parent == registration
        assert revised_response.schema == initial_response.schema
        assert revised_response.previous_response == initial_response
        assert revised_response.revision_justification == 'Leeeeerooooy Jeeeenkiiiinns'

        assert revised_response != initial_response
        assert not revised_response.updated_response_blocks.exists()
        assert set(revised_response.response_blocks.all()) == set(initial_response.response_blocks.all())

    def test_create_from_previous_response_notification(
            self, initial_response, admin_user, notification_recipients):
        send_mail = mails.send_mail
        with mock.patch.object(schema_response.mails, 'send_mail', autospec=True) as mock_send:
            mock_send.side_effect = send_mail  # implicitly test rendering
            schema_response.SchemaResponse.create_from_previous_response(
                previous_response=initial_response, initiator=admin_user
            )

        assert_notification_correctness(
            mock_send, mails.SCHEMA_RESPONSE_INITIATED, notification_recipients
        )

    @pytest.mark.parametrize(
        'invalid_response_state',
        [
            ApprovalStates.IN_PROGRESS,
            ApprovalStates.UNAPPROVED,
            ApprovalStates.PENDING_MODERATION,
            # The following states are, in-theory, unreachable, but check to be sure
            ApprovalStates.REJECTED,
            ApprovalStates.MODERATOR_REJECTED,
            ApprovalStates.COMPLETED,
        ]
    )
    def test_create_from_previous_response_fails_if_parent_has_unapproved_response(
            self, invalid_response_state, initial_response):
        # Making a valid revised response, then pushing the initial response into an
        # invalid state to ensure that `create_from_previous_response` fails if
        # *any* schema_response on the parent is unapproved
        intermediate_response = schema_response.SchemaResponse.create_from_previous_response(
            initiator=initial_response.initiator,
            previous_response=initial_response
        )
        intermediate_response.approvals_state_machine.set_state(ApprovalStates.APPROVED)
        intermediate_response.save()

        initial_response.approvals_state_machine.set_state(invalid_response_state)
        initial_response.save()
        with pytest.raises(PreviousSchemaResponseError):
            schema_response.SchemaResponse.create_from_previous_response(
                initiator=initial_response.initiator,
                previous_response=intermediate_response
            )


@pytest.mark.enable_bookmark_creation
@pytest.mark.django_db
class TestUpdateSchemaResponses():

    def test_all_responses_property(self, initial_response):
        assert initial_response.all_responses == INITIAL_SCHEMA_RESPONSES
        for block in initial_response.response_blocks.all():
            assert initial_response.all_responses[block.schema_key] == block.response

    def test_uodated_response_keys_property(self, initial_response, revised_response, schema):
        # initial_response "updates" all keys
        all_keys = set(
            RegistrationSchemaBlock.objects.filter(
                schema=schema, registration_response_key__isnull=False
            ).values_list('registration_response_key', flat=True)
        )

        assert initial_response.updated_response_keys == all_keys

        # No updated_responses on the standard revised_response
        assert not revised_response.updated_response_keys
        # Key shows up after update
        revised_response.update_responses({'q1': 'I has a new  answer'})
        assert revised_response.updated_response_keys == {'q1'}

    def test_update_responses(self, initial_response):
        assert initial_response.all_responses == INITIAL_SCHEMA_RESPONSES

        updated_responses = {
            'q1': 'Hello there',
            'q2': 'This is a new response',
            'q3': 'B',
            'q4': ['E'],
            'q5': 'Roonil Wazlib, et al',
            'q6': [{'file_id': '123456'}],
        }
        initial_response.approvals_state_machine.set_state(ApprovalStates.IN_PROGRESS)
        initial_response.save()
        initial_response.update_responses(updated_responses)

        initial_response.refresh_from_db()
        assert initial_response.all_responses == updated_responses
        for block in initial_response.response_blocks.all():
            assert block.response == updated_responses[block.schema_key]

    def test_update_to_initial_response_updates_response_blocks_in_place(self, initial_response):
        # Call set to force evaluation
        initial_block_ids = set(initial_response.response_blocks.values_list('id', flat=True))

        initial_response.approvals_state_machine.set_state(ApprovalStates.IN_PROGRESS)
        initial_response.save()
        initial_response.update_responses(
            {
                'q1': 'Hello there',
                'q2': 'This is a new response',
                'q3': 'B',
                'q4': ['E'],
                'q5': 'Roonil Wazlib, et al',
                'q6': [{'file_id': '123456'}],
            }
        )
        initial_response.refresh_from_db()
        updated_block_ids = set(initial_response.response_blocks.values_list('id', flat=True))
        assert initial_block_ids == updated_block_ids

    def test_initial_update_to_revised_response_creates_new_block(self, revised_response):
        q1_block = revised_response.response_blocks.get(schema_key='q1')
        other_blocks = set(revised_response.response_blocks.exclude(schema_key='q1'))

        revised_response.update_responses({'q1': 'Heeyo'})
        revised_response.refresh_from_db()

        updated_q1_block = revised_response.response_blocks.get(schema_key='q1')
        # Block for q1 should be a brand new block
        assert q1_block.id != updated_q1_block.id
        assert updated_q1_block.response == 'Heeyo'
        # All other blocks should be the same
        assert other_blocks == set(revised_response.response_blocks.exclude(schema_key='q1'))

    def test_update_to_previously_revised_response_updates_block(self, revised_response):
        revised_response.update_responses({'q1': 'Heeyo'})
        revised_response.refresh_from_db()
        updated_block = revised_response.response_blocks.get(schema_key='q1')

        revised_response.update_responses({'q1': 'Jokes!'})
        revised_response.refresh_from_db()
        assert revised_response.response_blocks.get(schema_key='q1').id == updated_block.id
        updated_block.refresh_from_db()
        assert updated_block.response == 'Jokes!'

    def test_update_without_change_is_noop(self, revised_response):
        original_block_ids = set(revised_response.response_blocks.values_list('id', flat=True))
        revised_response.update_responses(INITIAL_SCHEMA_RESPONSES)

        revised_response.refresh_from_db()
        updated_block_ids = set(revised_response.response_blocks.values_list('id', flat=True))
        assert updated_block_ids == original_block_ids
        assert not revised_response.updated_response_keys

    def test_revert_updated_response(self, revised_response):
        original_block = revised_response.response_blocks.get(schema_key='q1')
        revised_response.update_responses({'q1': 'whoops'})

        revised_response.refresh_from_db()
        updated_block = revised_response.response_blocks.get(schema_key='q1')

        revised_response.update_responses({'q1': INITIAL_SCHEMA_RESPONSES['q1']})
        revised_response.refresh_from_db()

        assert revised_response.response_blocks.get(schema_key='q1') == original_block
        assert not SchemaResponseBlock.objects.filter(id=updated_block.id).exists()
        assert 'q1' not in revised_response.updated_response_keys

    def test_update_with_mixed_modalities(self, revised_response):
        original_q2_block = revised_response.response_blocks.get(schema_key='q2')
        original_q3_block = revised_response.response_blocks.get(schema_key='q3')
        original_q4_block = revised_response.response_blocks.get(schema_key='q4')

        revised_response.update_responses({'q1': 'Heeyo', 'q4': ['D', 'E', 'F', 'G']})
        revised_response.refresh_from_db()
        updated_q1_block = revised_response.response_blocks.get(schema_key='q1')

        updated_responses = {
            'q1': 'Hello there',
            'q2': 'This is a new response',
            'q3': INITIAL_SCHEMA_RESPONSES['q3'],
            'q4': INITIAL_SCHEMA_RESPONSES['q4']
        }
        revised_response.update_responses(updated_responses)
        revised_response.refresh_from_db()

        assert revised_response.response_blocks.get(schema_key='q1').id == updated_q1_block.id
        assert revised_response.response_blocks.get(schema_key='q2').id != original_q2_block.id
        assert revised_response.response_blocks.get(schema_key='q3').id == original_q3_block.id
        assert revised_response.response_blocks.get(schema_key='q4').id == original_q4_block.id

    def test_update_with_unsupported_key_raises(self, revised_response):
        with pytest.raises(SchemaResponseUpdateError) as manager:
            revised_response.update_responses({'q7': 'sneaky'})

        assert manager.value.unsupported_keys == {'q7'}

    @pytest.mark.parametrize(
        'updated_responses',
        [
            {'q1': 'New Answer', 'q2': 'Another one', 'q7': 'Wrong key at end'},
            {'q7': 'Wrong key first', 'q1': 'New Answer', 'q2': 'Another one'},
            {'q1': 'New Answer', 'q7': 'Wrong key in the middle', 'q2': 'Another one'}
        ]
    )
    def test_update_with_unsupported_key_and_supported_keys_writes_and_raises(
            self, updated_responses, revised_response):
        with pytest.raises(SchemaResponseUpdateError):
            revised_response.update_responses(updated_responses)

        revised_response.refresh_from_db()
        assert revised_response.all_responses['q1'] == updated_responses['q1']
        assert revised_response.all_responses['q2'] == updated_responses['q2']

    def test_update_fails_with_invalid_response_types(self, revised_response):
        with pytest.raises(SchemaResponseUpdateError) as manager:
            revised_response.update_responses(
                {'q1': 1, 'q2': ['this is a list'], 'q3': 'B', 'q4': 'this is a string'}
            )

        assert set(manager.value.invalid_responses.keys()) == {'q1', 'q2', 'q4'}

    def test_update_fails_with_invalid_response_values(self, revised_response):
        with pytest.raises(SchemaResponseUpdateError) as manager:
            revised_response.update_responses(
                {'q3': 'Q', 'q4': ['D', 'A']}
            )

        assert set(manager.value.invalid_responses.keys()) == {'q3', 'q4'}

    @pytest.mark.parametrize(
        'invalid_response_state',
        [
            ApprovalStates.UNAPPROVED,
            ApprovalStates.PENDING_MODERATION,
            ApprovalStates.APPROVED,
            # The following states are, in-theory, unreachable, but check to be sure
            ApprovalStates.REJECTED,
            ApprovalStates.MODERATOR_REJECTED,
            ApprovalStates.COMPLETED,
        ]
    )
    def test_update_fails_if_state_is_invalid(self, invalid_response_state, initial_response):
        initial_response.approvals_state_machine.set_state(invalid_response_state)
        with pytest.raises(SchemaResponseStateError):
            initial_response.update_responses({'q1': 'harrumph'})

    def test_update_file_is_noop_if_no_change_in_ids(self, revised_response):
        revised_response.update_responses({'q6': [{'file_id': '123456'}, {'file_id': '654321'}]})
        revised_response.update_responses(
            {'q1': 'Real update', 'q6': [{'file_id': '654321'}, {'file_id': '123456'}]}
        )

        assert revised_response.all_responses['q1'] == 'Real update'
        assert revised_response.all_responses['q6'] == [{'file_id': '123456'}, {'file_id': '654321'}]


@pytest.mark.django_db
class TestDeleteSchemaResponse():

    def test_delete_schema_response_deletes_schema_response_blocks(self, initial_response):
        # initial_response is the only current source of SchemaResponseBlocks,
        # so all should be deleted
        initial_response.approvals_state_machine.set_state(ApprovalStates.IN_PROGRESS)
        initial_response.save()
        initial_response.delete()
        assert not SchemaResponseBlock.objects.exists()

    def test_delete_revised_response_only_deletes_updated_blocks(self, initial_response):
        revised_response = schema_response.SchemaResponse.create_from_previous_response(
            previous_response=initial_response,
            initiator=initial_response.initiator
        )
        revised_response.update_responses({'q1': 'blahblahblah', 'q2': 'whoopdedoo'})

        old_blocks = initial_response.response_blocks.all()
        updated_blocks = revised_response.updated_response_blocks.all()

        revised_response.delete()
        for block in old_blocks:
            assert SchemaResponseBlock.objects.filter(id=block.id).exists()
        for block in updated_blocks:
            assert not SchemaResponseBlock.objects.filter(id=block.id).exists()

    @pytest.mark.parametrize(
        'invalid_response_state',
        [
            ApprovalStates.UNAPPROVED,
            ApprovalStates.PENDING_MODERATION,
            ApprovalStates.APPROVED,
            # The following states are, in-theory, unreachable, but check to be sure
            ApprovalStates.REJECTED,
            ApprovalStates.MODERATOR_REJECTED,
            ApprovalStates.COMPLETED,
        ]
    )
    def test_delete_fails_if_state_is_invalid(self, invalid_response_state, initial_response):
        initial_response.approvals_state_machine.set_state(invalid_response_state)
        initial_response.save()
        with pytest.raises(SchemaResponseStateError):
            initial_response.delete()


@pytest.mark.django_db
class TestUnmoderatedSchemaResponseApprovalFlows():

    def test_submit_response_adds_pending_approvers(
            self, initial_response, admin_user, alternate_user):
        initial_response.approvals_state_machine.set_state(ApprovalStates.IN_PROGRESS)
        initial_response.update_responses({'q1': 'must change one response or can\'t submit'})
        initial_response.revision_justification = 'has for valid revision_justification for submission'
        initial_response.save()

        initial_response.submit(user=admin_user, required_approvers=[admin_user, alternate_user])

        assert initial_response.state is ApprovalStates.UNAPPROVED
        for user in [admin_user, alternate_user]:
            assert user in initial_response.pending_approvers.all()

    def test_submit_response_writes_schema_response_action(self, initial_response, admin_user):
        initial_response.approvals_state_machine.set_state(ApprovalStates.IN_PROGRESS)
        initial_response.update_responses({'q1': 'must change one response or can\'t submit'})
        initial_response.revision_justification = 'has for valid revision_justification for submission'
        initial_response.save()
        assert not initial_response.actions.exists()

        initial_response.submit(user=admin_user, required_approvers=[admin_user])

        new_action = initial_response.actions.last()
        assert new_action.creator == admin_user
        assert new_action.from_state == ApprovalStates.IN_PROGRESS.db_name
        assert new_action.to_state == ApprovalStates.UNAPPROVED.db_name
        assert new_action.trigger == SchemaResponseTriggers.SUBMIT.db_name

    def test_submit_response_notification(
            self, revised_response, admin_user, notification_recipients):
        revised_response.approvals_state_machine.set_state(ApprovalStates.IN_PROGRESS)
        revised_response.update_responses({'q1': 'must change one response or can\'t submit'})
        revised_response.revision_justification = 'has for valid revision_justification for submission'
        revised_response.save()

        send_mail = mails.send_mail
        with mock.patch.object(schema_response.mails, 'send_mail', autospec=True) as mock_send:
            mock_send.side_effect = send_mail  # implicitly test rendering
            revised_response.submit(user=admin_user, required_approvers=[admin_user])

        assert_notification_correctness(
            mock_send, mails.SCHEMA_RESPONSE_SUBMITTED, notification_recipients
        )

    def test_no_submit_notification_on_initial_response(self, initial_response, admin_user):
        initial_response.approvals_state_machine.set_state(ApprovalStates.IN_PROGRESS)
        initial_response.update_responses({'q1': 'must change one response or can\'t submit'})
        initial_response.revision_justification = 'has for valid revision_justification for submission'
        initial_response.save()
        with mock.patch.object(schema_response.mails, 'send_mail', autospec=True) as mock_send:
            initial_response.submit(user=admin_user, required_approvers=[admin_user])
        assert not mock_send.called

    def test_submit_response_requires_user(self, initial_response, admin_user):
        initial_response.approvals_state_machine.set_state(ApprovalStates.IN_PROGRESS)
        initial_response.save()
        with pytest.raises(PermissionsError):
            initial_response.submit(required_approvers=[admin_user])

    def test_submit_fails_with_invalid_response_value(self, initial_response, admin_user):
        initial_response.approvals_state_machine.set_state(ApprovalStates.IN_PROGRESS)
        initial_response.save()
        invalid_block = initial_response.response_blocks.get(schema_key='q1')
        invalid_block.response = 1
        invalid_block.save()

        with pytest.raises(SchemaResponseStateError):
            initial_response.submit(user=admin_user, required_approvers=[admin_user])

    def test_submit_fails_with_missing_required_response(self, initial_response, admin_user):
        initial_response.approvals_state_machine.set_state(ApprovalStates.IN_PROGRESS)
        initial_response.save()
        invalid_block = initial_response.response_blocks.get(schema_key='q1')
        invalid_block.response = ''
        invalid_block.save()

        with pytest.raises(SchemaResponseStateError):
            initial_response.submit(user=admin_user, required_approvers=[admin_user])

    def test_submit_response_requires_required_approvers(self, initial_response, admin_user):
        initial_response.approvals_state_machine.set_state(ApprovalStates.IN_PROGRESS)
        initial_response.save()
        with pytest.raises(ValueError):
            initial_response.submit(user=admin_user)

    def test_non_parent_admin_cannot_submit_response(self, initial_response, alternate_user):
        initial_response.approvals_state_machine.set_state(ApprovalStates.IN_PROGRESS)
        initial_response.save()
        with pytest.raises(PermissionsError):
            initial_response.submit(user=alternate_user)

    def test_approve_response_requires_all_approvers(
            self, initial_response, admin_user, alternate_user):
        initial_response.approvals_state_machine.set_state(ApprovalStates.UNAPPROVED)
        initial_response.save()
        initial_response.pending_approvers.add(admin_user, alternate_user)

        initial_response.approve(user=admin_user)
        assert initial_response.state is ApprovalStates.UNAPPROVED

        initial_response.approve(user=alternate_user)
        assert initial_response.state is ApprovalStates.APPROVED

    def test_approve_response_writes_schema_response_action(
            self, initial_response, admin_user, alternate_user):
        initial_response.approvals_state_machine.set_state(ApprovalStates.UNAPPROVED)
        initial_response.save()
        initial_response.pending_approvers.add(admin_user, alternate_user)

        initial_response.approve(user=admin_user)

        # Confirm that action for first "approve" still has to_state of UNAPPROVED
        new_action = initial_response.actions.last()
        assert new_action.creator == admin_user
        assert new_action.from_state == ApprovalStates.UNAPPROVED.db_name
        assert new_action.to_state == ApprovalStates.UNAPPROVED.db_name
        assert new_action.trigger == SchemaResponseTriggers.APPROVE.db_name

        initial_response.approve(user=alternate_user)

        # Confirm that action for final "approve" has to_state of APPROVED
        new_action = initial_response.actions.last()
        assert new_action.creator == alternate_user
        assert new_action.from_state == ApprovalStates.UNAPPROVED.db_name
        assert new_action.to_state == ApprovalStates.APPROVED.db_name
        assert new_action.trigger == SchemaResponseTriggers.APPROVE.db_name

        # Confirm that final approval writes only one action
        assert initial_response.actions.filter(
            trigger=SchemaResponseTriggers.APPROVE.db_name
        ).count() == 2

    def test_approve_response_notification(
            self, revised_response, admin_user, alternate_user, notification_recipients):
        revised_response.approvals_state_machine.set_state(ApprovalStates.UNAPPROVED)
        revised_response.save()
        revised_response.pending_approvers.add(admin_user, alternate_user)

        send_mail = mails.send_mail
        with mock.patch.object(schema_response.mails, 'send_mail', autospec=True) as mock_send:
            mock_send.side_effect = send_mail  # implicitly test rendering
            revised_response.approve(user=admin_user)
            assert not mock_send.called  # Should only send email on final approval
            revised_response.approve(user=alternate_user)

        assert_notification_correctness(
            mock_send, mails.SCHEMA_RESPONSE_APPROVED, notification_recipients
        )

    def test_no_approve_notification_on_initial_response(self, initial_response, admin_user):
        initial_response.approvals_state_machine.set_state(ApprovalStates.UNAPPROVED)
        initial_response.save()
        initial_response.pending_approvers.add(admin_user)

        with mock.patch.object(schema_response.mails, 'send_mail', autospec=True) as mock_send:
            initial_response.approve(user=admin_user)
        assert not mock_send.called

    def test_approve_response_requires_user(self, initial_response, admin_user):
        initial_response.approvals_state_machine.set_state(ApprovalStates.UNAPPROVED)
        initial_response.save()
        initial_response.pending_approvers.add(admin_user)
        with pytest.raises(PermissionsError):
            initial_response.approve()

    def test_non_approver_cannot_approve_response(
            self, initial_response, admin_user, alternate_user):
        initial_response.approvals_state_machine.set_state(ApprovalStates.UNAPPROVED)
        initial_response.save()
        initial_response.pending_approvers.add(admin_user)

        with pytest.raises(PermissionsError):
            initial_response.approve(user=alternate_user)

    def test_reject_response_moves_state_to_in_progress(self, initial_response, admin_user, alternate_user):
        initial_response.approvals_state_machine.set_state(ApprovalStates.UNAPPROVED)
        initial_response.save()
        initial_response.pending_approvers.add(admin_user, alternate_user)

        # Implicitly confirm that only one reject call is needed to advance state
        initial_response.reject(user=admin_user)
        assert initial_response.state is ApprovalStates.IN_PROGRESS

    def test_reject_response_clears_pending_approvers(
            self, initial_response, admin_user, alternate_user):
        initial_response.approvals_state_machine.set_state(ApprovalStates.UNAPPROVED)
        initial_response.save()
        initial_response.pending_approvers.add(admin_user, alternate_user)

        initial_response.reject(user=admin_user)

        assert not initial_response.pending_approvers.exists()

    def test_reject_response_writes_schema_response_action(self, initial_response, admin_user):
        initial_response.approvals_state_machine.set_state(ApprovalStates.UNAPPROVED)
        initial_response.pending_approvers.add(admin_user)
        initial_response.save()

        initial_response.reject(user=admin_user)

        new_action = initial_response.actions.last()
        assert new_action.creator == admin_user
        assert new_action.from_state == ApprovalStates.UNAPPROVED.db_name
        assert new_action.to_state == ApprovalStates.IN_PROGRESS.db_name
        assert new_action.trigger == SchemaResponseTriggers.ADMIN_REJECT.db_name

    def test_reject_response_notification(
            self, revised_response, admin_user, notification_recipients):
        revised_response.approvals_state_machine.set_state(ApprovalStates.UNAPPROVED)
        revised_response.save()
        revised_response.pending_approvers.add(admin_user)

        send_mail = mails.send_mail
        with mock.patch.object(schema_response.mails, 'send_mail', autospec=True) as mock_send:
            mock_send.side_effect = send_mail  # implicitly test rendering
            revised_response.reject(user=admin_user)

        assert_notification_correctness(
            mock_send, mails.SCHEMA_RESPONSE_REJECTED, notification_recipients
        )

    def test_no_reject_notification_on_initial_response(self, initial_response, admin_user):
        initial_response.approvals_state_machine.set_state(ApprovalStates.UNAPPROVED)
        initial_response.save()
        initial_response.pending_approvers.add(admin_user)

        with mock.patch.object(schema_response.mails, 'send_mail', autospec=True) as mock_send:
            initial_response.reject(user=admin_user)
        assert not mock_send.called

    def test_reject_response_requires_user(self, initial_response, admin_user):
        initial_response.approvals_state_machine.set_state(ApprovalStates.UNAPPROVED)
        initial_response.save()
        initial_response.pending_approvers.add(admin_user)

        with pytest.raises(PermissionsError):
            initial_response.reject()

    def test_non_approver_cannnot_reject_response(
            self, initial_response, admin_user, alternate_user):
        initial_response.approvals_state_machine.set_state(ApprovalStates.UNAPPROVED)
        initial_response.save()
        initial_response.pending_approvers.add(admin_user)

        with pytest.raises(PermissionsError):
            initial_response.reject(user=alternate_user)

    def test_approver_cannot_call_accept_directly(self, initial_response, admin_user):
        initial_response.approvals_state_machine.set_state(ApprovalStates.UNAPPROVED)
        initial_response.save()
        initial_response.pending_approvers.add(admin_user)

        with pytest.raises(MachineError):
            initial_response.accept(user=admin_user)

    def test_internal_accept_advances_state(self, initial_response, admin_user, alternate_user):
        initial_response.approvals_state_machine.set_state(ApprovalStates.UNAPPROVED)
        initial_response.save()
        initial_response.pending_approvers.add(admin_user, alternate_user)

        initial_response.accept()

        assert initial_response.state is ApprovalStates.APPROVED

    def test_internal_accept_clears_pending_approvers(self, initial_response, admin_user):
        initial_response.approvals_state_machine.set_state(ApprovalStates.UNAPPROVED)
        initial_response.save()
        initial_response.pending_approvers.add(admin_user)

        initial_response.accept()

        assert not initial_response.pending_approvers.exists()


@pytest.mark.django_db
class TestModeratedSchemaResponseApprovalFlows():

    @pytest.fixture
    def provider(self):
        provider = RegistrationProviderFactory()
        provider.update_group_permissions()
        _ensure_subscriptions(provider)
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

    def test_moderated_response_requires_moderation(self, initial_response, admin_user):
        initial_response.approvals_state_machine.set_state(ApprovalStates.UNAPPROVED)
        initial_response.save()
        initial_response.pending_approvers.add(admin_user)

        initial_response.approve(user=admin_user)

        assert initial_response.state is ApprovalStates.PENDING_MODERATION

    def test_schema_response_action_to_state_following_moderated_approve_is_pending_moderation(
            self, initial_response, admin_user):
        initial_response.approvals_state_machine.set_state(ApprovalStates.UNAPPROVED)
        initial_response.save()
        initial_response.pending_approvers.add(admin_user)

        initial_response.approve(user=admin_user)

        new_action = initial_response.actions.last()
        assert new_action.creator == admin_user
        assert new_action.from_state == ApprovalStates.UNAPPROVED.db_name
        assert new_action.to_state == ApprovalStates.PENDING_MODERATION.db_name
        assert new_action.trigger == SchemaResponseTriggers.APPROVE.db_name

    def test_accept_notification_sent_on_admin_approval(self, revised_response, admin_user):
        revised_response.approvals_state_machine.set_state(ApprovalStates.UNAPPROVED)
        revised_response.save()
        revised_response.pending_approvers.add(admin_user)

        send_mail = mails.send_mail
        with mock.patch.object(schema_response.mails, 'send_mail', autospec=True) as mock_send:
            mock_send.side_effect = send_mail
            revised_response.approve(user=admin_user)
        assert mock_send.called

    def test_moderators_notified_on_admin_approval(self, revised_response, admin_user, moderator):
        revised_response.approvals_state_machine.set_state(ApprovalStates.UNAPPROVED)
        revised_response.save()
        revised_response.pending_approvers.add(admin_user)

        store_emails = emails.store_emails
        with mock.patch.object(emails, 'store_emails', autospec=True) as mock_store:
            mock_store.side_effect = store_emails
            revised_response.approve(user=admin_user)

        assert mock_store.called
        assert mock_store.call_args[0][0] == [moderator._id]

    def test_no_moderator_notification_on_admin_approval_of_initial_response(
            self, initial_response, admin_user):
        initial_response.approvals_state_machine.set_state(ApprovalStates.UNAPPROVED)
        initial_response.save()
        initial_response.pending_approvers.add(admin_user)

        with mock.patch.object(emails, 'store_emails', autospec=True) as mock_store:
            initial_response.approve(user=admin_user)
        assert not mock_store.called

    def test_moderator_accept(self, initial_response, moderator):
        initial_response.approvals_state_machine.set_state(ApprovalStates.PENDING_MODERATION)
        initial_response.save()

        initial_response.accept(user=moderator)

        assert initial_response.state is ApprovalStates.APPROVED

    def test_moderator_accept_writes_schema_response_action(self, initial_response, moderator):
        initial_response.approvals_state_machine.set_state(ApprovalStates.PENDING_MODERATION)
        initial_response.save()

        initial_response.accept(user=moderator)

        new_action = initial_response.actions.last()
        assert new_action.creator == moderator
        assert new_action.from_state == ApprovalStates.PENDING_MODERATION.db_name
        assert new_action.to_state == ApprovalStates.APPROVED.db_name
        assert new_action.trigger == SchemaResponseTriggers.ACCEPT.db_name

    def test_moderator_accept_notification(
            self, revised_response, moderator, notification_recipients):
        revised_response.approvals_state_machine.set_state(ApprovalStates.PENDING_MODERATION)
        revised_response.save()

        send_mail = mails.send_mail
        with mock.patch.object(schema_response.mails, 'send_mail', autospec=True) as mock_send:
            mock_send.side_effect = send_mail  # implicitly test rendering
            revised_response.accept(user=moderator)

        assert_notification_correctness(
            mock_send, mails.SCHEMA_RESPONSE_APPROVED, notification_recipients
        )

    def test_no_moderator_accept_notification_on_initial_response(
            self, initial_response, moderator):
        initial_response.approvals_state_machine.set_state(ApprovalStates.PENDING_MODERATION)
        initial_response.save()

        with mock.patch.object(schema_response.mails, 'send_mail', autospec=True) as mock_send:
            initial_response.accept(user=moderator)
        assert not mock_send.called

    def test_moderator_reject(self, initial_response, admin_user, moderator):
        initial_response.approvals_state_machine.set_state(ApprovalStates.PENDING_MODERATION)
        initial_response.save()

        initial_response.reject(user=moderator)

        assert initial_response.state is ApprovalStates.IN_PROGRESS

    def test_moderator_reject_writes_schema_response_action(
            self, initial_response, admin_user, moderator):
        initial_response.approvals_state_machine.set_state(ApprovalStates.PENDING_MODERATION)
        initial_response.save()

        initial_response.reject(user=moderator)

        new_action = initial_response.actions.last()
        assert new_action.creator == moderator
        assert new_action.from_state == ApprovalStates.PENDING_MODERATION.db_name
        assert new_action.to_state == ApprovalStates.IN_PROGRESS.db_name
        assert new_action.trigger == SchemaResponseTriggers.MODERATOR_REJECT.db_name

    def test_moderator_reject_notification(
            self, revised_response, moderator, notification_recipients):
        revised_response.approvals_state_machine.set_state(ApprovalStates.PENDING_MODERATION)
        revised_response.save()

        send_mail = mails.send_mail
        with mock.patch.object(schema_response.mails, 'send_mail', autospec=True) as mock_send:
            mock_send.side_effect = send_mail  # implicitly test rendering
            revised_response.reject(user=moderator)

        assert_notification_correctness(
            mock_send, mails.SCHEMA_RESPONSE_REJECTED, notification_recipients
        )

    def test_no_moderator_reject_notification_on_initial_response(
            self, initial_response, moderator):
        initial_response.approvals_state_machine.set_state(ApprovalStates.PENDING_MODERATION)
        initial_response.save()

        with mock.patch.object(schema_response.mails, 'send_mail', autospec=True) as mock_send:
            initial_response.reject(user=moderator)
        assert not mock_send.called

    def test_moderator_cannot_submit(self, initial_response, moderator):
        initial_response.approvals_state_machine.set_state(ApprovalStates.IN_PROGRESS)
        initial_response.save()

        with pytest.raises(PermissionsError):
            initial_response.submit(user=moderator, required_approvers=[moderator])

    def test_moderator_cannot_approve_in_unapproved_state(
            self, initial_response, admin_user, moderator):
        initial_response.approvals_state_machine.set_state(ApprovalStates.UNAPPROVED)
        initial_response.save()

        with pytest.raises(PermissionsError):
            initial_response.approve(user=moderator)

    def test_moderator_cannot_reject_in_unapproved_state(
            self, initial_response, admin_user, moderator):
        initial_response.approvals_state_machine.set_state(ApprovalStates.UNAPPROVED)
        initial_response.save()

        with pytest.raises(PermissionsError):
            initial_response.reject(user=moderator)

    def test_admin_cannot_accept_in_pending_moderation(self, initial_response, admin_user):
        initial_response.approvals_state_machine.set_state(ApprovalStates.PENDING_MODERATION)
        initial_response.save()

        with pytest.raises(PermissionsError):
            initial_response.accept(user=admin_user)

    def test_admin_cannot_reject_in_pending_moderation(self, initial_response, admin_user):
        initial_response.approvals_state_machine.set_state(ApprovalStates.PENDING_MODERATION)
        initial_response.save()

        with pytest.raises(PermissionsError):
            initial_response.reject(user=admin_user)

    def test_user_required_to_accept_in_pending_moderation(self, initial_response, admin_user):
        initial_response.approvals_state_machine.set_state(ApprovalStates.PENDING_MODERATION)
        initial_response.save()

        with pytest.raises(PermissionsError):
            initial_response.accept()
