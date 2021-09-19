import pytest

from osf_tests.factories import (
    AuthUserFactory,
    RegistrationFactory,
    SchemaResponseFactory,
    SchemaResponseActionFactory
)

from osf.utils.workflows import SchemaResponseTriggers, ApprovalStates

@pytest.mark.django_db
@pytest.mark.enable_quickfiles_creation
class TestSchemaResponseActionList:

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def registration(self):
        return RegistrationFactory()

    @pytest.fixture()
    def schema_response(self, registration):
        return SchemaResponseFactory(
            registration=registration,
            initiator=registration.creator,
        )

    @pytest.fixture()
    def unapproved_schema_response(self, schema_response, user):
        schema_response.approvals_state_machine.set_state(ApprovalStates.UNAPPROVED)
        schema_response.pending_approvers.add(user)
        schema_response.save()
        return schema_response

    @pytest.fixture()
    def schema_response_action(self, schema_response):
        return SchemaResponseActionFactory(
            target=schema_response,
        )

    def make_payload(self, schema_response, trigger):
        return {
            'data':
                {
                    'type': 'schema-response-actions',
                    'attributes': {
                        'trigger': trigger.db_name,
                        'comment': "It's Party time!",
                    },
                    'relationships': {
                        'target': {
                            'data': {
                                'id': schema_response._id,
                                'type': 'schema-responses'
                            }
                        }
                    }
                }
        }

    @pytest.fixture()
    def url(self, schema_response):
        return f'/v2/schema_responses/{schema_response._id}/actions/'

    def test_schema_response_action_submit(self, app, registration, schema_response, user, url):
        assert schema_response.reviews_state == ApprovalStates.IN_PROGRESS.db_name
        registration.add_contributor(user, 'admin')
        assert not schema_response.pending_approvers.count()
        payload = self.make_payload(schema_response=schema_response, trigger=SchemaResponseTriggers.SUBMIT)
        resp = app.post_json_api(url, payload, auth=user.auth, expect_errors=True)
        assert resp.status_code == 201
        schema_response.refresh_from_db()
        assert schema_response.reviews_state == ApprovalStates.UNAPPROVED.db_name

    def test_schema_response_action_approve(self, app, registration, unapproved_schema_response, user, url):
        payload = self.make_payload(schema_response=unapproved_schema_response, trigger=SchemaResponseTriggers.APPROVE)
        resp = app.post_json_api(url, payload, auth=user.auth, expect_errors=True)
        assert resp.status_code == 201
        unapproved_schema_response.refresh_from_db()
        assert unapproved_schema_response.reviews_state == ApprovalStates.APPROVED.db_name

    def test_schema_response_action_accept(self, app, registration, unapproved_schema_response, user, url):
        """
        Accept behavior is explained in the docstring for _validate_accept_trigger function. There are 3 methods of
        using this trigger.
        """
        unapproved_schema_response.pending_approvers.clear()
        payload = self.make_payload(schema_response=unapproved_schema_response, trigger=SchemaResponseTriggers.ACCEPT)
        resp = app.post_json_api(url, payload, auth=user.auth, expect_errors=True)
        assert resp.status_code == 201
        unapproved_schema_response.refresh_from_db()
        assert unapproved_schema_response.reviews_state == ApprovalStates.APPROVED.db_name

    def test_schema_response_action_moderator_reject(self, app, registration, unapproved_schema_response, user, url):
        payload = self.make_payload(schema_response=unapproved_schema_response, trigger=SchemaResponseTriggers.MODERATOR_REJECT)
        resp = app.post_json_api(url, payload, auth=user.auth, expect_errors=True)
        assert resp.status_code == 201
        unapproved_schema_response.refresh_from_db()
        assert unapproved_schema_response.reviews_state == ApprovalStates.IN_PROGRESS.db_name

    def test_schema_response_action_admin_reject(self, app, registration, unapproved_schema_response, user, url):
        payload = self.make_payload(schema_response=unapproved_schema_response, trigger=SchemaResponseTriggers.ADMIN_REJECT)
        resp = app.post_json_api(url, payload, auth=user.auth, expect_errors=True)
        assert resp.status_code == 201
        unapproved_schema_response.refresh_from_db()
        assert unapproved_schema_response.reviews_state == ApprovalStates.IN_PROGRESS.db_name

    def test_schema_response_action_list(self, app, schema_response_action, schema_response, user, url):
        resp = app.get(url, auth=user.auth)
        assert resp.status_code == 200
        data = resp.json['data']
        assert len(data) == 1
        assert schema_response_action._id == data[0]['id']

    @pytest.mark.parametrize(
        'permission,expected_response',
        [
            (None, 200, ),
            ('read', 200, ),
            ('write', 200, ),
            ('admin', 200, ),
        ]
    )
    def test_schema_response_action_auth_get(self, app, registration, permission, user, expected_response, url):
        if permission:
            registration.add_contributor(user, permission)
        resp = app.get(url, auth=user.auth, expect_errors=True)
        assert resp.status_code == expected_response

    @pytest.mark.parametrize(
        'permission,expected_response',
        [
            (None, 403, ),
            ('read', 403, ),
            ('write', 403, ),
            ('admin', 201, ),
        ]
    )
    def test_schema_response_action_auth_post(self, app, registration, schema_response, permission, user, expected_response, url):
        if permission:
            registration.add_contributor(user, permission)

        payload = self.make_payload(schema_response=schema_response, trigger=SchemaResponseTriggers.SUBMIT)
        resp = app.post_json_api(url, payload, auth=user.auth, expect_errors=True)
        assert resp.status_code == expected_response

    @pytest.mark.parametrize(
        'permission,expected_response',
        [
            (None, 405, ),
            ('read', 405, ),
            ('write', 405, ),
            ('admin', 405, ),
        ]
    )
    def test_schema_response_action_auth_patch(self, app, registration, permission, user, expected_response, url):
        if permission:
            registration.add_contributor(user, permission)
        resp = app.patch_json_api(url, auth=user.auth, expect_errors=True)
        assert resp.status_code == expected_response

    @pytest.mark.parametrize(
        'permission,expected_response',
        [
            (None, 405, ),
            ('read', 405, ),
            ('write', 405, ),
            ('admin', 405, ),
        ]
    )
    def test_schema_response_action_delete(self, app, registration, permission, user, expected_response, url):
        if permission:
            registration.add_contributor(user, permission)
        resp = app.delete_json_api(url, auth=user.auth, expect_errors=True)
        assert resp.status_code == expected_response
