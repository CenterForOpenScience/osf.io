import pytest

from osf.models import MetaSchema
from scripts.send_erpc_entrants_email import get_erpc_participants
from framework.auth.core import Auth
from osf_tests.factories import AuthUserFactory, ProjectFactory

from tests.utils import assert_items_equal


@pytest.mark.django_db
class TestERPCParticipantEmail:

    def test_get_erpc_participants(self):
        creator = AuthUserFactory()
        admin_contributor = AuthUserFactory()
        write_contributor = AuthUserFactory()
        read_contributor = AuthUserFactory()

        project = ProjectFactory(creator=creator)
        project.add_contributor(admin_contributor, permissions=['admin'], auth=Auth(creator))
        project.add_contributor(write_contributor, permissions=['write'], auth=Auth(creator))
        project.add_contributor(read_contributor, permissions=['read'], auth=Auth(creator))
        project.save()
        schema = MetaSchema.objects.get(name='Election Research Preacceptance Competition', active=False)

        registration = project.register_node(schema=schema, auth=Auth(creator), data='')
        registration.save()

        gathered_participant_emails = get_erpc_participants()
        expected_participant_emails = [admin_contributor.username, creator.username, write_contributor.username]

        assert_items_equal(gathered_participant_emails, expected_participant_emails)
        assert read_contributor not in gathered_participant_emails
