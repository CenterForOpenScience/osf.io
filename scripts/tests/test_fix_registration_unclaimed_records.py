import pytest

from framework.auth.core import Auth
from osf_tests.factories import PreprintFactory, UserFactory, ProjectFactory
from scripts.fix_registration_unclaimed_records import main as fix_records_script
from osf_tests.utils import mock_archive

pytestmark = pytest.mark.django_db

class TestFixRegistrationUnclaimedRecords:

    @pytest.fixture()
    def user(self):
        return UserFactory()

    @pytest.fixture()
    def project(self, user, auth, fake):
        return ret

    @pytest.fixture()
    def auth(self, user):
        return Auth(user)

    @pytest.fixture()
    def project(self, user, auth):
        return ProjectFactory(creator=user)
    
    @pytest.fixture()
    def contributor_unregistered(self, user, auth, project):
        ret = project.add_unregistered_contributor(fullname='Johnny Git Gud', email='ford.prefect@hitchhikers.com', auth=auth)
        project.save()
        return ret

    @pytest.fixture()
    def contributor_unregistered_no_email(self, user, auth, project):
        ret = project.add_unregistered_contributor(fullname='Johnny B. Bard', email='', auth=auth)
        project.save()
        return ret

    @pytest.fixture()
    def registration(self, project, contributor_unregistered, contributor_unregistered_no_email):
        with mock_archive(project, autoapprove=True) as registration:
            return registration

    def test_migrate_bad_data(self, user, project, registration, contributor_unregistered, contributor_unregistered_no_email):
        contributor_unregistered.refresh_from_db()
        contributor_unregistered_no_email.refresh_from_db()
 
        # confirm data exists
        assert contributor_unregistered.unclaimed_records.get(registration._id, None)
        assert contributor_unregistered_no_email.unclaimed_records.get(registration._id, None)

        # clear registration data
        del contributor_unregistered.unclaimed_records[registration._id]
        contributor_unregistered.save()

        # clear registration AND node data for second contributor
        contributor_unregistered_no_email.unclaimed_records = {}

        # change name to ensure given name passes on
        contributor_unregistered_no_email.given_name = 'Shenanigans'
        contributor_unregistered_no_email.save()

        # Force refresh and confirm data gone
        contributor_unregistered.refresh_from_db()
        contributor_unregistered_no_email.refresh_from_db()
        assert not contributor_unregistered.unclaimed_records.get(registration._id, False)
        assert contributor_unregistered_no_email.unclaimed_records == {}

        # Run script
        fix_records_script()

        # reload again
        contributor_unregistered.refresh_from_db()
        contributor_unregistered_no_email.refresh_from_db()

        record_one = contributor_unregistered.unclaimed_records.get(registration._id)
        assert record_one
        assert record_one == contributor_unregistered.unclaimed_records.get(project._id)

        record_two = contributor_unregistered_no_email.unclaimed_records.get(registration._id)
        assert record_two 
        assert record_two['name'] == 'Shenanigans'
        assert record_two['email'] is None
