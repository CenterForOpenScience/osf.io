import pytest
from osf.management.commands.migrate_preprint_affiliation import assign_affiliations_to_preprints
from osf_tests.factories import (
    PreprintFactory,
    InstitutionFactory,
    AuthUserFactory,
)


@pytest.mark.django_db
class TestAssignAffiliationsToPreprints:

    @pytest.fixture()
    def institution(self):
        return InstitutionFactory()

    @pytest.fixture()
    def user_with_affiliation(self, institution):
        user = AuthUserFactory()
        user.add_or_update_affiliated_institution(institution)
        user.save()
        return user

    @pytest.fixture()
    def user_without_affiliation(self):
        return AuthUserFactory()

    @pytest.fixture()
    def preprint_with_affiliated_contributor(self, user_with_affiliation):
        preprint = PreprintFactory()
        preprint.add_contributor(
            user_with_affiliation,
            permissions='admin',
            visible=True
        )
        return preprint

    @pytest.fixture()
    def preprint_with_non_affiliated_contributor(self, user_without_affiliation):
        preprint = PreprintFactory()
        preprint.add_contributor(
            user_without_affiliation,
            permissions='admin',
            visible=True
        )
        return preprint

    @pytest.mark.parametrize('dry_run', [True, False])
    def test_assign_affiliations_with_affiliated_contributor(self, preprint_with_affiliated_contributor, institution, dry_run):
        preprint = preprint_with_affiliated_contributor
        preprint.affiliated_institutions.clear()
        preprint.save()

        assign_affiliations_to_preprints(dry_run=dry_run)

        if dry_run:
            assert not preprint.affiliated_institutions.exists()
        else:
            assert institution in preprint.affiliated_institutions.all()

    @pytest.mark.parametrize('dry_run', [True, False])
    def test_no_affiliations_for_non_affiliated_contributor(self, preprint_with_non_affiliated_contributor, dry_run):
        preprint = preprint_with_non_affiliated_contributor
        preprint.affiliated_institutions.clear()
        preprint.save()

        assign_affiliations_to_preprints(dry_run=dry_run)

        assert not preprint.affiliated_institutions.exists()

    @pytest.mark.parametrize('dry_run', [True, False])
    def test_exclude_contributor_by_guid(self, preprint_with_affiliated_contributor, user_with_affiliation, institution, dry_run):
        preprint = preprint_with_affiliated_contributor
        preprint.affiliated_institutions.clear()
        preprint.save()

        assert user_with_affiliation.get_affiliated_institutions()
        assert user_with_affiliation in preprint.contributors.all()
        exclude_guids = {user._id for user in preprint.contributors.all()}

        assign_affiliations_to_preprints(exclude_guids=exclude_guids, dry_run=dry_run)

        assert not preprint.affiliated_institutions.exists()

    @pytest.mark.parametrize('dry_run', [True, False])
    def test_affiliations_from_multiple_contributors(self, institution, dry_run):
        institution_not_include = InstitutionFactory()
        read_contrib = AuthUserFactory()
        read_contrib.add_or_update_affiliated_institution(institution_not_include)
        read_contrib.save()

        write_contrib = AuthUserFactory()
        write_contrib.add_or_update_affiliated_institution(institution)
        write_contrib.save()

        admin_contrib = AuthUserFactory()
        institution2 = InstitutionFactory()
        admin_contrib.add_or_update_affiliated_institution(institution2)
        admin_contrib.save()

        preprint = PreprintFactory()
        preprint.affiliated_institutions.clear()
        preprint.add_contributor(read_contrib, permissions='read', visible=True)
        preprint.add_contributor(write_contrib, permissions='write', visible=True)
        preprint.add_contributor(admin_contrib, permissions='admin', visible=True)
        preprint.save()

        assign_affiliations_to_preprints(dry_run=dry_run)

        if dry_run:
            assert not preprint.affiliated_institutions.exists()
        else:
            affiliations = set(preprint.affiliated_institutions.all())
            assert affiliations == {institution, institution2}
            assert institution_not_include not in affiliations
