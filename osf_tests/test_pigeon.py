from unittest import mock
import pytest
from osf_tests.factories import RegistrationFactory, AuthUserFactory, EmbargoFactory, NodeFactory
from osf.external.internet_archive.tasks import _archive_to_ia, _update_ia_metadata


@pytest.mark.django_db
class TestPigeon:

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def registration(self):
        return RegistrationFactory()

    @pytest.fixture()
    def registration_with_child(self, registration):
        NodeFactory(parent=registration)
        return registration

    @pytest.fixture()
    def schema_response(self, registration):
        return registration.schema_responses.last()

    @pytest.fixture()
    def embargo(self):
        embargo = EmbargoFactory()
        embargo.accept()
        return embargo

    @pytest.mark.enable_enqueue_task
    @pytest.mark.enable_implicit_clean
    def test_pigeon_sync_metadata(self, mock_pigeon, registration, mock_celery):
        registration.is_public = True
        registration.ia_url = 'http://archive.org/details/osf-registrations-guid0-v1'
        registration.title = 'Jefferies'
        registration.save()

        mock_celery.assert_called_with(
            _update_ia_metadata,
            (
                registration._id,
                {
                    'title': 'Jefferies',
                    'modified': str(registration.modified)
                }
            ),
            {},
            celery=True
        )

    @pytest.mark.enable_enqueue_task
    @pytest.mark.enable_implicit_clean
    def test_pigeon_archive_immediately(self, registration, mock_pigeon, mock_celery):
        registration.is_public = True
        registration.save()

        mock_celery.assert_called_with(_archive_to_ia, (registration._id,), {}, celery=True)

    @pytest.mark.enable_enqueue_task
    @pytest.mark.enable_implicit_clean
    def test_pigeon_archive_embargo(self, embargo, mock_pigeon, mock_celery):
        embargo._get_registration().terminate_embargo()
        guid = embargo._get_registration()._id

        mock_celery.assert_called_with(_archive_to_ia, (guid,), {}, celery=True)

    @pytest.mark.enable_enqueue_task
    @pytest.mark.enable_implicit_clean
    def test_pigeon_archive_schema_response(self, schema_response, mock_pigeon, mock_celery, registration_with_child):
        schema_response.pending_approvers.add(schema_response.parent.creator)
        schema_response.approve(user=schema_response.parent.creator)
        schema_response.save()

        mock_celery.assert_has_calls([
            mock.call(_archive_to_ia, (schema_response.parent._id,), {}, celery=True),
            mock.call(_archive_to_ia, (registration_with_child.nodes[0]._id,), {}, celery=True)
        ], any_order=True)
