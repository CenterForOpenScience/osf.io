
import pytest

from api.base.settings.defaults import API_BASE
from osf.utils.workflows import ApprovalStates
from osf.models import SchemaResponse
from osf_tests.factories import (
    ProjectFactory,
    RegistrationFactory,
    AuthUserFactory,
)
from osf_tests.utils import get_default_test_schema


@pytest.mark.django_db
class TestRegistrationResponses:

    INITIAL_SCHEMA_RESPONSES = {
        'q1': 'Some answer',
        'q2': 'Some even longer answer',
        'q3': 'A',
        'q4': ['D', 'G'],
        'q5': None,
        'q6': None,
    }

    @pytest.fixture
    def admin(self):
        return AuthUserFactory()

    @pytest.fixture
    def registration(self, admin):
        return RegistrationFactory(schema=get_default_test_schema(), creator=admin)

    @pytest.fixture
    def approved_schema_response(self, registration):
        response = registration.schema_responses.last()
        response.state = ApprovalStates.IN_PROGRESS
        response.update_responses(self.INITIAL_SCHEMA_RESPONSES)
        response.state = ApprovalStates.APPROVED
        response.save()
        return response

    @pytest.fixture
    def revised_schema_response(self, approved_schema_response):
        response = SchemaResponse.create_from_previous_response(
            previous_response=approved_schema_response,
            initiator=approved_schema_response.initiator
        )
        response.update_responses({'q1': 'updated', 'q2': 'answers'})
        return response

    @pytest.fixture
    def nested_registration(self, registration):
        return RegistrationFactory(
            project=ProjectFactory(parent=registration.registered_from),
            parent=registration,
            is_public=True,
        )

    def get_registration_detail_url(self, registration):
        return f'/{API_BASE}registrations/{registration._id}/'

    def test_registration_responses_surfaces_latest_approved_responses(
            self, app, registration, approved_schema_response, revised_schema_response, admin):

        resp = app.get(self.get_registration_detail_url(registration), auth=admin.auth)
        responses = resp.json['data']['attributes']['registration_responses']
        assert responses == approved_schema_response.all_responses
        assert registration.registration_responses != approved_schema_response.all_responses

        revised_schema_response.state = ApprovalStates.APPROVED
        revised_schema_response.save()

        resp = app.get(self.get_registration_detail_url(registration), auth=admin.auth)
        responses = resp.json['data']['attributes']['registration_responses']
        assert responses == revised_schema_response.all_responses
        assert registration.registration_responses != revised_schema_response.all_responses

    def test_nested_registration_surfaces_root_schema_responses(
            self, app, nested_registration, approved_schema_response):
        assert not nested_registration.schema_responses.exists()

        resp = app.get(self.get_registration_detail_url(nested_registration))

        responses = resp.json['data']['attributes']['registration_responses']
        assert responses == approved_schema_response.all_responses
        assert nested_registration.registration_responses != approved_schema_response.all_responses

    @pytest.mark.parametrize('revision_state', ApprovalStates)
    def test_nested_registration_surfaces_root_revision_state(
            self, app, nested_registration, approved_schema_response, revision_state):
        approved_schema_response.state = revision_state
        approved_schema_response.save()

        resp = app.get(self.get_registration_detail_url(nested_registration))
        assert resp.json['data']['attributes']['revision_state'] == revision_state.db_name

    def test_original_response_relationship(
            self, app, registration, approved_schema_response, revised_schema_response, admin):
        resp = app.get(self.get_registration_detail_url(registration), auth=admin.auth)

        original_response_id = resp.json['data']['relationships']['original_response']['data']['id']
        assert original_response_id == approved_schema_response._id

    @pytest.mark.parametrize('revised_response_state', ApprovalStates)
    def test_latest_response_relationship(
            self, app, registration, approved_schema_response, revised_schema_response, revised_response_state, admin):
        revised_schema_response.state = revised_response_state
        revised_schema_response.save()
        if revised_response_state is ApprovalStates.APPROVED:
            expected_id = revised_schema_response._id
        else:
            expected_id = approved_schema_response._id

        resp = app.get(self.get_registration_detail_url(registration), auth=admin.auth)
        latest_response_id = resp.json['data']['relationships']['latest_response']['data']['id']
        assert latest_response_id == expected_id

    def test_original_and_latest_response_relationship_on_nested_registration(
            self, app, nested_registration, approved_schema_response, revised_schema_response):
        revised_schema_response.state = ApprovalStates.APPROVED
        revised_schema_response.save()

        resp = app.get(self.get_registration_detail_url(nested_registration))

        original_response_id = resp.json['data']['relationships']['original_response']['data']['id']
        latest_response_id = resp.json['data']['relationships']['latest_response']['data']['id']
        assert original_response_id == approved_schema_response._id
        assert latest_response_id == revised_schema_response._id
