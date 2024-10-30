import pytest
from osf.management.commands.assign_creator_affiliations_to_preprints import assign_creator_affiliations_to_preprints
from osf.models import Preprint, Institution, OSFUser
from osf_tests.factories import PreprintFactory, InstitutionFactory, AuthUserFactory

@pytest.mark.django_db
class TestAssignCreatorAffiliationsToPreprints:

    @pytest.fixture()
    def institution(self):
        return InstitutionFactory()

    @pytest.fixture()
    def user_with_affiliation(self, institution):
        user = AuthUserFactory()
        user.affiliated_institutions.add(institution)
        user.save()
        return user

    @pytest.fixture()
    def user_without_affiliation(self):
        return AuthUserFactory()

    @pytest.fixture()
    def preprint_with_affiliated_creator(self, user_with_affiliation):
        return PreprintFactory(creator=user_with_affiliation)

    @pytest.fixture()
    def preprint_with_non_affiliated_creator(self, user_without_affiliation):
        return PreprintFactory(creator=user_without_affiliation)

    @pytest.mark.parametrize("dry_run", [True, False])
    def test_assign_affiliations_with_affiliated_creator(self, preprint_with_affiliated_creator, institution, dry_run):
        assert preprint_with_affiliated_creator.affiliated_institutions.count() == 0

        assign_creator_affiliations_to_preprints(dry_run=dry_run)

        if dry_run:
            assert preprint_with_affiliated_creator.affiliated_institutions.count() == 0
        else:
            assert institution in preprint_with_affiliated_creator.affiliated_institutions.all()

    @pytest.mark.parametrize("dry_run", [True, False])
    def test_no_affiliations_for_non_affiliated_creator(self, preprint_with_non_affiliated_creator, dry_run):
        assign_creator_affiliations_to_preprints(dry_run=dry_run)
        assert preprint_with_non_affiliated_creator.affiliated_institutions.count() == 0

    @pytest.mark.parametrize("dry_run", [True, False])
    def test_exclude_creator_by_guid(self, preprint_with_affiliated_creator, institution, dry_run):
        exclude_guid = preprint_with_affiliated_creator.creator._id
        assign_creator_affiliations_to_preprints(exclude_guids={exclude_guid}, dry_run=dry_run)

        assert preprint_with_affiliated_creator.affiliated_institutions.count() == 0
