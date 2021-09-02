import pytest

from framework.exceptions import PermissionsError

from nose.tools import assert_raises

from osf.models.metaschema import RegistrationSchemaBlock
from osf.models.schema_response import InvalidSchemaResponseStateError, SchemaResponse
from osf.models.schema_response_block import SchemaResponseBlock
from osf.utils.workflows import ApprovalStates
from osf_tests.factories import AuthUserFactory, RegistrationFactory
from osf_tests.utils import get_default_test_schema

# See osft_tests.utils.default_test_schema for block types and valid answers
INITIAL_SCHEMA_RESPONSES = {
    'q1': 'Some answer',
    'q2': 'Some even longer answer',
    'q3': 'A',
    'q4': ['D', 'G'],
    'q5': None,
    'q6': None
}


@pytest.fixture
def schema():
    return get_default_test_schema()

@pytest.fixture
def registration(schema):
    return RegistrationFactory(schema=schema)

@pytest.fixture
def schema_response(registration):
    response = SchemaResponse.create_initial_response(
        initiator=registration.creator,
        parent=registration,
        schema=registration.registration_schema
    )
    response.update_responses(INITIAL_SCHEMA_RESPONSES)
    return response

@pytest.mark.enable_bookmark_creation
@pytest.mark.django_db
class TestCreateSchemaResponse():

    def test_create_initial_response_sets_attributes(self, registration):
        response = SchemaResponse.create_initial_response(
            initiator=registration.creator,
            parent=registration,
            schema=registration.registration_schema
        )

        assert response.parent == registration
        assert response in registration.schema_responses.all()
        assert response.schema == registration.registration_schema
        assert response.initiator == registration.creator
        assert not response.submitted_timestamp

    def test_create_initial_response_assigns_response_blocks_and_source_revision(
            self, registration):
        assert not SchemaResponseBlock.objects.exists()
        response = SchemaResponse.create_initial_response(
            initiator=registration.creator,
            parent=registration,
            schema=registration.registration_schema
        )
        # No previous SchemaResponseBlocks means all SchemaResponseBlocks in existence
        # were created by the create_initial_response call
        created_response_blocks = set(SchemaResponseBlock.objects.all())

        # Confirm that the all of the created blocks have the created response as their
        # source revision and that response_blocks has all of the created blocks
        assert created_response_blocks == set(response.updated_response_blocks.all())
        assert created_response_blocks == set(response.response_blocks.all())

    def test_create_initial_response_creates_blocks_for_each_schema_question(self, registration):
        assert not SchemaResponseBlock.objects.exists()
        schema = registration.registration_schema
        SchemaResponse.create_initial_response(
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
        SchemaResponse.create_initial_response(
            initiator=registration.creator,
            parent=registration,
            schema=registration.registration_schema
        )

        with assert_raises(AssertionError):
            SchemaResponse.create_initial_response(
                initiator=registration.creator,
                parent=registration,
                schema=schema
            )

    def test_create_initial_response_for_different_parent(self, registration, schema):
        first_response = SchemaResponse.create_initial_response(
            initiator=registration.creator,
            parent=registration,
            schema=schema
        )

        alternate_registration = RegistrationFactory(schema=schema)
        alternate_registration_response = SchemaResponse.create_initial_response(
            initiator=alternate_registration.creator,
            parent=alternate_registration,
            schema=schema,
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

    def test_create_from_previous_response(self, schema_response):
        schema_response.approvals_state_machine.set_state(ApprovalStates.APPROVED)
        schema_response.save()

        revised_response = SchemaResponse.create_from_previous_response(
            initiator=schema_response.initiator,
            previous_response=schema_response,
            justification='Leeeeerooooy Jeeeenkiiiinns'
        )

        assert revised_response.initiator == schema_response.initiator
        assert revised_response.parent == schema_response.parent
        assert revised_response.schema == schema_response.schema
        assert revised_response.revision_justification == 'Leeeeerooooy Jeeeenkiiiinns'

        assert revised_response != schema_response
        assert not revised_response.updated_response_blocks.exists()
        assert set(revised_response.response_blocks.all()) == set(schema_response.response_blocks.all())

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
            self, invalid_response_state, schema_response):
        # Making a valid revised response, then pushing the initial response into an
        # invalid state to ensure that `create_from_previous_response` fails if
        # *any* schema_response on the parent is unapproved
        schema_response.approvals_state_machine.set_state(ApprovalStates.APPROVED)
        schema_response.save()

        intermediate_response = SchemaResponse.create_from_previous_response(
            initiator=schema_response.initiator,
            previous_response=schema_response
        )
        intermediate_response.approvals_state_machine.set_state(ApprovalStates.APPROVED)
        intermediate_response.save()

        schema_response.approvals_state_machine.set_state(invalid_response_state)
        schema_response.save()
        with assert_raises(InvalidSchemaResponseStateError):
            SchemaResponse.create_from_previous_response(
                initiator=schema_response.initiator,
                previous_response=intermediate_response
            )


@pytest.mark.enable_bookmark_creation
@pytest.mark.django_db
class TestUpdateSchemaResponses():

    @pytest.fixture
    def revised_response(self, schema_response):
        schema_response.approvals_state_machine.set_state(ApprovalStates.APPROVED)
        schema_response.save()
        return SchemaResponse.create_from_previous_response(
            initiator=schema_response.initiator,
            previous_response=schema_response,
            justification='Leeeeerooooy Jeeeenkiiiinns'
        )

    def test_all_responses_property(self, schema_response):
        assert schema_response.all_responses == INITIAL_SCHEMA_RESPONSES
        for block in schema_response.response_blocks.all():
            assert schema_response.all_responses[block.schema_key] == block.response

    def test_uodated_response_keys_property(self, schema_response, revised_response, schema):
        # initial_response "updates" all keys
        all_keys = set(
            RegistrationSchemaBlock.objects.filter(
                schema=schema, registration_response_key__isnull=False
            ).values_list('registration_response_key', flat=True)
        )

        assert schema_response.updated_response_keys == all_keys

        # No updated_responses on the standard revised_response
        assert not revised_response.updated_response_keys
        # Key shows up after update
        revised_response.update_responses({'q1': 'I has a new  answer'})
        assert revised_response.updated_response_keys == {'q1'}

    def test_update_responses(self, schema_response):
        assert schema_response.all_responses == INITIAL_SCHEMA_RESPONSES

        updated_responses = {
            'q1': 'Hello there',
            'q2': 'This is a new response',
            'q3': 'B',
            'q4': ['E'],
            'q5': [schema_response.initiator.id],
            'q6': 'SomeFile',
        }
        schema_response.update_responses(updated_responses)

        schema_response.refresh_from_db()
        assert schema_response.all_responses == updated_responses
        for block in schema_response.response_blocks.all():
            assert block.response == updated_responses[block.schema_key]

    def test_update_to_initial_response_updates_response_blocks_in_place(self, schema_response):
        # Call set to force evaluation
        initial_block_ids = set(schema_response.response_blocks.values_list('id', flat=True))

        schema_response.update_responses(
            {
                'q1': 'Hello there',
                'q2': 'This is a new response',
                'q3': 'B',
                'q4': ['E'],
                'q5': [schema_response.initiator.id],
                'q6': 'SomeFile'
            }
        )
        schema_response.refresh_from_db()
        updated_block_ids = set(schema_response.response_blocks.values_list('id', flat=True))
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

    def test_update_with_unsupported_key_raises(self, schema_response):
        with assert_raises(ValueError):
            schema_response.update_responses({'q7': 'sneaky'})

    @pytest.mark.parametrize(
        'updated_responses',
        [
            {'q1': 'New Answer', 'q2': 'Another one', 'q7': 'Wrong key at end'},
            {'q7': 'Wrong key first', 'q1': 'New Answer', 'q2': 'Another one'},
            {'q1': 'New Answer', 'q7': 'Wrong key in the middle', 'q2': 'Another one'}
        ]
    )
    def test_update_with_unsupported_key_and_supported_keys_writes_and_raises(
            self, updated_responses, schema_response):
        with assert_raises(ValueError):
            schema_response.update_responses(updated_responses)

        schema_response.refresh_from_db()
        assert schema_response.all_responses['q1'] == updated_responses['q1']
        assert schema_response.all_responses['q2'] == updated_responses['q2']

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
    def test_update_fails_if_state_is_invalid(self, invalid_response_state, schema_response):
        schema_response.approvals_state_machine.set_state(invalid_response_state)
        with assert_raises(InvalidSchemaResponseStateError):
            schema_response.update_responses({'q1': 'harrumph'})

@pytest.mark.enable_bookmark_creation
@pytest.mark.django_db
class TestUnmoderatedSchemaResponseApprovalFlows():

    @pytest.fixture
    def alternate_user(self):
        return AuthUserFactory()

    def test_submit_response_adds_pending_approvers(self, schema_response, alternate_user):
        assert schema_response.state is ApprovalStates.IN_PROGRESS
        schema_response.submit(
            user=schema_response.initiator,
            required_approvers=[schema_response.initiator, alternate_user]
        )

        schema_response.refresh_from_db()
        assert schema_response.state is ApprovalStates.UNAPPROVED
        for user in [schema_response.initiator, alternate_user]:
            assert user in schema_response.pending_approvers.all()

    def test_approve_response_requires_all_approvers(self, schema_response, alternate_user):
        schema_response.submit(
            user=schema_response.initiator,
            required_approvers=[schema_response.initiator, alternate_user],
        )

        schema_response.approve(user=schema_response.initiator)
        schema_response.refresh_from_db()
        assert schema_response.state is ApprovalStates.UNAPPROVED

        schema_response.approve(user=alternate_user)
        schema_response.refresh_from_db()
        assert schema_response.state is ApprovalStates.APPROVED

    def test_non_approver_cannot_approve_response(self, schema_response, alternate_user):
        schema_response.submit(
            user=schema_response.initiator,
            required_approvers=[schema_response.initiator]
        )
        schema_response.refresh_from_db()

        with assert_raises(PermissionsError):
            schema_response.approve(user=alternate_user)

    def test_reject_response_moves_state_to_in_progress(self, schema_response, alternate_user):
        schema_response.submit(
            user=schema_response.initiator,
            required_approvers=[schema_response.initiator, alternate_user],
        )

        # Implicitly confirm that only one reject call is needed to advance state
        schema_response.reject(user=schema_response.initiator)
        schema_response.refresh_from_db()

        assert schema_response.state is ApprovalStates.IN_PROGRESS

    def test_reject_response_clears_pending_approvers(self, schema_response, alternate_user):
        schema_response.submit(
            user=schema_response.initiator,
            required_approvers=[schema_response.initiator, alternate_user],
        )

        schema_response.reject(user=schema_response.initiator)
        schema_response.refresh_from_db()

        assert not schema_response.pending_approvers.exists()

    def test_non_approver_cannnot_reject_response(self, schema_response, alternate_user):
        schema_response.submit(
            user=schema_response.initiator,
            required_approvers=[schema_response.initiator]
        )
        schema_response.refresh_from_db()

        with assert_raises(PermissionsError):
            schema_response.reject(user=alternate_user)

    def test_approver_cannot_call_accept_directly(self, schema_response):
        schema_response.submit(
            user=schema_response.initiator,
            required_approvers=[schema_response.initiator]
        )
        schema_response.refresh_from_db()

        with assert_raises(PermissionsError):
            schema_response.accept(user=schema_response.initiator)


@pytest.mark.enable_bookmark_creation
@pytest.mark.django_db
class TestModeratedSchemaResponseApprovalFlows():
    pass
