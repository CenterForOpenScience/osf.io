import pytest

from nose.tools import assert_raises

from api.providers.workflows import Workflows
from framework.exceptions import PermissionsError
from osf.exceptions import PreviousPendingSchemaResponseError, SchemaResponseStateError
from osf.migrations import update_provider_auth_groups
from osf.models import RegistrationSchema, RegistrationSchemaBlock, SchemaResponse, SchemaResponseBlock
from osf.utils.workflows import ApprovalStates, SchemaResponseTriggers
from osf_tests.factories import AuthUserFactory, RegistrationFactory, RegistrationProviderFactory
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
def admin_user():
    return AuthUserFactory()

@pytest.fixture
def schema():
    return get_default_test_schema()


@pytest.fixture
def registration(schema, admin_user):
    return RegistrationFactory(schema=schema, creator=admin_user)


@pytest.fixture
def schema_response(registration):
    response = SchemaResponse.create_initial_response(
        initiator=registration.creator,
        parent=registration
    )
    response.update_responses(INITIAL_SCHEMA_RESPONSES)
    return response


@pytest.mark.enable_bookmark_creation
@pytest.mark.django_db
class TestCreateSchemaResponse():

    def test_create_initial_response_sets_attributes(self, registration, schema):
        response = SchemaResponse.create_initial_response(
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
        response = SchemaResponse.create_initial_response(
            initiator=registration.creator,
            parent=registration
        )

        assert response.schema == registration.registration_schema

    def test_create_initial_response_assigns_response_blocks_and_source_revision(
            self, registration, schema):
        assert not SchemaResponseBlock.objects.exists()
        response = SchemaResponse.create_initial_response(
            initiator=registration.creator,
            parent=registration,
            schema=schema
        )
        # No previous SchemaResponseBlocks means all SchemaResponseBlocks in existence
        # were created by the create_initial_response call
        created_response_blocks = set(SchemaResponseBlock.objects.all())

        # Confirm that the all of the created blocks have the created response as their
        # source revision and that response_blocks has all of the created blocks
        assert created_response_blocks == set(response.updated_response_blocks.all())
        assert created_response_blocks == set(response.response_blocks.all())

    def test_create_initial_response_fails_if_no_schema_and_no_parent_schema(self, registration):
        registration.registered_schema.clear()
        registration.save()
        with assert_raises(ValueError):
            SchemaResponse.create_initial_response(
                initiator=registration.creator,
                parent=registration
            )

    def test_create_initial_response_fails_if_schema_and_parent_schema_mismatch(self, registration):
        alt_schema = RegistrationSchema.objects.exclude(
            id=registration.registration_schema.id
        ).first()
        with assert_raises(ValueError):
            SchemaResponse.create_initial_response(
                initiator=registration.creator,
                parent=registration,
                schema=alt_schema
            )

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
        )

        with assert_raises(PreviousPendingSchemaResponseError):
            SchemaResponse.create_initial_response(
                initiator=registration.creator,
                parent=registration,
            )

    def test_create_initial_response_for_different_parent(self, registration):
        schema = registration.registration_schema
        first_response = SchemaResponse.create_initial_response(
            initiator=registration.creator,
            parent=registration,
        )

        alternate_registration = RegistrationFactory(schema=schema)
        alternate_registration_response = SchemaResponse.create_initial_response(
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

    def test_create_from_previous_response(self, registration, schema_response):
        schema_response.approvals_state_machine.set_state(ApprovalStates.APPROVED)
        schema_response.save()
        revised_response = SchemaResponse.create_from_previous_response(
            initiator=registration.creator,
            previous_response=schema_response,
            justification='Leeeeerooooy Jeeeenkiiiinns'
        )

        assert revised_response.initiator == registration.creator
        assert revised_response.parent == registration
        assert revised_response.schema == schema_response.schema
        assert revised_response.previous_response == schema_response
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
        with assert_raises(PreviousPendingSchemaResponseError):
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
        # schema_response "updates" all keys
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

    def test_update_to_schema_response_updates_response_blocks_in_place(self, schema_response):
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
        with assert_raises(SchemaResponseStateError):
            schema_response.update_responses({'q1': 'harrumph'})


@pytest.mark.django_db
class TestDeleteSchemaResponse():

    def test_delete_schema_response_deletes_schema_response_blocks(self, schema_response):
        # schema_response is the only current source of SchemaResponseBlocks,
        # so all should be deleted
        schema_response.delete()
        assert not SchemaResponseBlock.objects.exists()

    def test_delete_revised_response_only_deletes_updated_blocks(self, schema_response):
        schema_response.approvals_state_machine.set_state(ApprovalStates.APPROVED)
        schema_response.save()

        revised_response = SchemaResponse.create_from_previous_response(
            previous_response=schema_response,
            initiator=schema_response.initiator
        )
        revised_response.update_responses({'q1': 'blahblahblah', 'q2': 'whoopdedoo'})

        old_blocks = schema_response.response_blocks.all()
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
    def test_delete_fails_if_state_is_invalid(self, invalid_response_state, schema_response):
        schema_response.approvals_state_machine.set_state(invalid_response_state)
        with assert_raises(SchemaResponseStateError):
            schema_response.delete()


@pytest.mark.enable_bookmark_creation
@pytest.mark.django_db
class TestUnmoderatedSchemaResponseApprovalFlows():

    @pytest.fixture
    def alternate_user(self):
        return AuthUserFactory()

    def test_submit_response_adds_pending_approvers(
            self, schema_response, admin_user, alternate_user):
        assert schema_response.state is ApprovalStates.IN_PROGRESS
        schema_response.submit(user=admin_user, required_approvers=[admin_user, alternate_user])

        assert schema_response.state is ApprovalStates.UNAPPROVED
        for user in [schema_response.initiator, alternate_user]:
            assert user in schema_response.pending_approvers.all()

    def test_submit_response_writes_schema_response_action(self, schema_response, admin_user):
        assert not schema_response.actions.exists()
        schema_response.submit(user=admin_user, required_approvers=[admin_user])

        new_action = schema_response.actions.last()
        assert new_action.creator == admin_user
        assert new_action.from_state == ApprovalStates.IN_PROGRESS.db_name
        assert new_action.to_state == ApprovalStates.UNAPPROVED.db_name
        assert new_action.trigger == SchemaResponseTriggers.SUBMIT.db_name

    def test_submit_response_requires_user(self, schema_response, admin_user):
        with assert_raises(ValueError):
            schema_response.submit(required_approvers=[admin_user])

    def test_submit_resposne_requires_required_approvers(self, schema_response, admin_user):
        with assert_raises(ValueError):
            schema_response.submit(user=admin_user)

    def test_non_parent_admin_cannot_submit_response(self, schema_response, alternate_user):
        with assert_raises(PermissionsError):
            schema_response.submit(user=alternate_user)

    def test_approve_response_requires_all_approvers(
            self, schema_response, admin_user, alternate_user):
        schema_response.submit(user=admin_user, required_approvers=[admin_user, alternate_user])

        schema_response.approve(user=schema_response.initiator)
        assert schema_response.state is ApprovalStates.UNAPPROVED

        schema_response.approve(user=alternate_user)
        assert schema_response.state is ApprovalStates.APPROVED

    def test_approve_response_writes_schema_response_action(
            self, schema_response, admin_user, alternate_user):
        schema_response.submit(user=admin_user, required_approvers=[admin_user, alternate_user])
        schema_response.approve(user=admin_user)

        # Confirm that action for first "approve" still has to_state of UNAPPROVED
        new_action = schema_response.actions.last()
        assert new_action.creator == admin_user
        assert new_action.from_state == ApprovalStates.UNAPPROVED.db_name
        assert new_action.to_state == ApprovalStates.UNAPPROVED.db_name
        assert new_action.trigger == SchemaResponseTriggers.APPROVE.db_name

        schema_response.approve(user=alternate_user)

        # Confifm that action for final "approve" has to_state of APPROVED
        new_action = schema_response.actions.last()
        assert new_action.creator == alternate_user
        assert new_action.from_state == ApprovalStates.UNAPPROVED.db_name
        assert new_action.to_state == ApprovalStates.APPROVED.db_name
        assert new_action.trigger == SchemaResponseTriggers.APPROVE.db_name

        # Confirm that final approval writes only one action
        assert schema_response.actions.filter(
            trigger=SchemaResponseTriggers.APPROVE.db_name
        ).count() == 2

    def test_approve_response_requires_user(self, schema_response, admin_user):
        schema_response.submit(user=admin_user, required_approvers=[admin_user])
        with assert_raises(ValueError):
            schema_response.approve()

    def test_non_approver_cannot_approve_response(
            self, schema_response, admin_user, alternate_user):
        schema_response.submit(user=admin_user, required_approvers=[admin_user])

        with assert_raises(PermissionsError):
            schema_response.approve(user=alternate_user)

    def test_reject_response_moves_state_to_in_progress(self, schema_response, admin_user, alternate_user):
        schema_response.submit(user=admin_user, required_approvers=[admin_user, alternate_user])

        # Implicitly confirm that only one reject call is needed to advance state
        schema_response.reject(user=admin_user)
        assert schema_response.state is ApprovalStates.IN_PROGRESS

    def test_reject_response_clears_pending_approvers(
            self, schema_response, admin_user, alternate_user):
        schema_response.submit(user=admin_user, required_approvers=[admin_user, alternate_user])
        schema_response.reject(user=schema_response.initiator)

        assert not schema_response.pending_approvers.exists()

    def test_reject_response_writes_schema_response_action(self, schema_response, admin_user):
        schema_response.submit(user=admin_user, required_approvers=[admin_user])
        schema_response.reject(user=admin_user)
        new_action = schema_response.actions.last()

        assert new_action.creator == admin_user
        assert new_action.from_state == ApprovalStates.UNAPPROVED.db_name
        assert new_action.to_state == ApprovalStates.IN_PROGRESS.db_name
        assert new_action.trigger == SchemaResponseTriggers.ADMIN_REJECT.db_name

    def test_reject_response_requires_user(self, schema_response, admin_user):
        schema_response.submit(user=admin_user, required_approvers=[admin_user])
        with assert_raises(ValueError):
            schema_response.reject()

    def test_non_approver_cannnot_reject_response(
            self, schema_response, admin_user, alternate_user):
        schema_response.submit(user=admin_user, required_approvers=[admin_user])

        with assert_raises(PermissionsError):
            schema_response.reject(user=alternate_user)

    def test_approver_cannot_call_accept_directly(self, schema_response, admin_user):
        schema_response.submit(user=admin_user, required_approvers=[admin_user])

        with assert_raises(ValueError):
            schema_response.accept(user=schema_response.initiator)

    def test_internal_accept_advances_state(self, schema_response, admin_user, alternate_user):
        schema_response.submit(user=admin_user, required_approvers=[admin_user, alternate_user])
        schema_response.accept()

        assert schema_response.state is ApprovalStates.APPROVED

    def test_internal_accept_clears_pending_approvers(self, schema_response, admin_user):
        schema_response.submit(user=admin_user, required_approvers=[admin_user])
        schema_response.accept()
        assert not schema_response.pending_approvers.exists()


@pytest.mark.django_db
class TestModeratedSchemaResponseApprovalFlows():

    @pytest.fixture
    def provider(self):
        provider = RegistrationProviderFactory()
        update_provider_auth_groups()
        provider.reviews_workflow = Workflows.PRE_MODERATION.value
        provider.save()
        return provider

    @pytest.fixture
    def moderator(self, provider):
        moderator = AuthUserFactory()
        provider.get_group('moderator').user_set.add(moderator)
        provider.save()
        return moderator

    @pytest.fixture
    def moderated_registration(self, schema, admin_user, provider):
        return RegistrationFactory(schema=schema, creator=admin_user, provider=provider)

    @pytest.fixture
    def moderated_response(self, moderated_registration):
        return SchemaResponse.create_initial_response(
            initiator=moderated_registration.creator,
            parent=moderated_registration,
        )

    def test_moderated_response_requires_moderation(self, moderated_response, admin_user):
        moderated_response.submit(user=admin_user, required_approvers=[admin_user])
        moderated_response.approve(user=admin_user)

        assert moderated_response.state is ApprovalStates.PENDING_MODERATION

    def test_schema_response_action_to_state_following_moderated_approve_is_pending_moderation(
            self, moderated_response, admin_user):
        moderated_response.submit(user=admin_user, required_approvers=[admin_user])
        moderated_response.approve(user=admin_user)

        new_action = moderated_response.actions.last()
        assert new_action.creator == admin_user
        assert new_action.from_state == ApprovalStates.UNAPPROVED.db_name
        assert new_action.to_state == ApprovalStates.PENDING_MODERATION.db_name
        assert new_action.trigger == SchemaResponseTriggers.APPROVE.db_name

    def test_moderator_accept(self, moderated_response, admin_user, moderator):
        moderated_response.submit(user=admin_user, required_approvers=[admin_user])
        moderated_response.approve(user=admin_user)
        moderated_response.accept(user=moderator)

        assert moderated_response.state is ApprovalStates.APPROVED

    def test_moderator_accept_writes_schema_response_action(
            self, moderated_response, admin_user, moderator):
        moderated_response.submit(user=admin_user, required_approvers=[admin_user])
        moderated_response.approve(user=admin_user)
        moderated_response.accept(user=moderator)

        new_action = moderated_response.actions.last()
        assert new_action.creator == moderator
        assert new_action.from_state == ApprovalStates.PENDING_MODERATION.db_name
        assert new_action.to_state == ApprovalStates.APPROVED.db_name
        assert new_action.trigger == SchemaResponseTriggers.ACCEPT.db_name

    def test_moderator_reject(self, moderated_response, admin_user, moderator):
        moderated_response.submit(user=admin_user, required_approvers=[admin_user])
        moderated_response.approve(user=admin_user)
        moderated_response.reject(user=moderator)

        assert moderated_response.state is ApprovalStates.IN_PROGRESS

    def test_moderator_reject_writes_schema_response_action(
            self, moderated_response, admin_user, moderator):
        moderated_response.submit(user=admin_user, required_approvers=[admin_user])
        moderated_response.approve(user=admin_user)
        moderated_response.reject(user=moderator)

        new_action = moderated_response.actions.last()
        assert new_action.creator == moderator
        assert new_action.from_state == ApprovalStates.PENDING_MODERATION.db_name
        assert new_action.to_state == ApprovalStates.IN_PROGRESS.db_name
        assert new_action.trigger == SchemaResponseTriggers.MODERATOR_REJECT.db_name

    def test_moderator_cannot_submit(self, moderated_response, moderator):
        with assert_raises(PermissionsError):
            moderated_response.submit(user=moderator, required_approvers=[moderator])

    def test_moderator_cannot_approve_in_unapproved_state(
            self, moderated_response, admin_user, moderator):
        moderated_response.submit(user=admin_user, required_approvers=[admin_user])
        with assert_raises(PermissionsError):
            moderated_response.approve(user=moderator)

    def test_moderator_cannot_reject_in_unapproved_state(
            self, moderated_response, admin_user, moderator):
        moderated_response.submit(user=admin_user, required_approvers=[admin_user])
        with assert_raises(PermissionsError):
            moderated_response.reject(user=moderator)

    def test_admin_cannot_accept_in_pending_moderation(self, moderated_response, admin_user):
        moderated_response.submit(user=admin_user, required_approvers=[admin_user])
        moderated_response.approve(user=admin_user)
        with assert_raises(PermissionsError):
            moderated_response.accept(user=admin_user)

    def test_admin_cannot_reject_in_pending_moderation(self, moderated_response, admin_user):
        moderated_response.submit(user=admin_user, required_approvers=[admin_user])
        moderated_response.approve(user=admin_user)
        with assert_raises(PermissionsError):
            moderated_response.reject(user=admin_user)

    def test_user_required_to_accept_in_pending_moderation(self, moderated_response, admin_user):
        moderated_response.submit(user=admin_user, required_approvers=[admin_user])
        moderated_response.approve(user=admin_user)
        with assert_raises(ValueError):
            moderated_response.accept()
