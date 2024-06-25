import pytest
from osf_tests.factories import (
    PreprintFactory,
    UserFactory,
    InstitutionFactory,
)
from osf.exceptions import UserNotAffiliatedError, ValidationError
from framework.auth import Auth


@pytest.mark.django_db
class TestPreprintInstitutionalAffiliation:
    """
    Tests for preprint model to handle updating InstitutionalAffiliationMixin
    """

    @pytest.fixture()
    def institution(self):
        return InstitutionFactory()

    @pytest.fixture()
    def user(self, institution):
        user = UserFactory()
        user.add_or_update_affiliated_institution(institution)
        return user

    @pytest.fixture()
    def user_without_affiliation(self):
        return UserFactory()

    @pytest.fixture()
    def preprint(self, user):
        preprint = PreprintFactory()
        preprint.add_permission(user, 'admin')
        return preprint

    def test_add_institution_that_does_not_exist(self, preprint, user):
        with pytest.raises(ValidationError):
            preprint.add_affiliated_institution(None, user)

    def test_remove_nonexistent_affiliation(self, preprint, institution, user):
        assert not preprint.remove_affiliated_institution(institution, user)

    def test_add_affiliated_institution_unaffiliated_user(self, preprint, institution, user_without_affiliation):
        with pytest.raises(UserNotAffiliatedError):
            preprint.add_affiliated_institution(institution, user_without_affiliation)

        assert not preprint.is_affiliated_with_institution(institution)

    def test_add_and_remove_affiliated_institution(self, preprint, institution, user):
        preprint.add_affiliated_institution(institution, user)
        assert preprint.is_affiliated_with_institution(institution)

        was_removed = preprint.remove_affiliated_institution(institution, user)
        assert was_removed
        assert not preprint.is_affiliated_with_institution(institution)

    def test_update_institutional_affiliation(self, preprint, institution, user):
        new_institution = InstitutionFactory()
        user.add_or_update_affiliated_institution(new_institution)

        institution_ids = [institution._id, new_institution._id]
        preprint.update_institutional_affiliation(Auth(user), institution_ids)

        assert preprint.is_affiliated_with_institution(institution)
        assert preprint.is_affiliated_with_institution(new_institution)

        institution_ids = [new_institution._id]
        preprint.update_institutional_affiliation(Auth(user), institution_ids)

        assert not preprint.is_affiliated_with_institution(institution)
        assert preprint.is_affiliated_with_institution(new_institution)

    def test_permission_errors_during_affiliation_update(self, preprint, institution, user_without_affiliation):
        with pytest.raises(UserNotAffiliatedError):
            preprint.add_affiliated_institution(institution, user_without_affiliation)
