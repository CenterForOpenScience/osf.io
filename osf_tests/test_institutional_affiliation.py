import pytest
from django.utils import timezone

from framework.auth import Auth
from osf.models import Preprint
from osf_tests.factories import (
    DraftRegistrationFactory,
    PreprintFactory,
    ProjectFactory,
    UserFactory,
    InstitutionFactory,
)
from osf.exceptions import UserNotAffiliatedError


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

    def test_permission_errors_during_affiliation_update(self, preprint, institution, user_without_affiliation):
        with pytest.raises(UserNotAffiliatedError):
            preprint.add_affiliated_institution(institution, user_without_affiliation)


@pytest.mark.django_db
class TestGetAffiliatedInstitutions:
    """
    get_affiliated_institutions() hides deactivated institutions by default, so they stay off
    the front end and out of search. Callers that must not drop an affiliation an object already
    has metadata and DOIs carrying a ROR id pass include_deactivated=True
    """

    @staticmethod
    def _deactivate(institution):
        institution.deactivated = timezone.now()
        institution.save()

    @pytest.fixture()
    def active_institution(self):
        return InstitutionFactory()

    @pytest.fixture()
    def institution_to_deactivate(self):
        return InstitutionFactory()

    @pytest.fixture()
    def user(self, active_institution, institution_to_deactivate):
        user = UserFactory()
        user.add_or_update_affiliated_institution(active_institution)
        user.add_or_update_affiliated_institution(institution_to_deactivate)
        return user

    @pytest.fixture(params=['preprint', 'node', 'draft_registration'])
    def resource(self, request, user, active_institution, institution_to_deactivate):
        if request.param == 'preprint':
            resource = PreprintFactory(creator=user)
        elif request.param == 'node':
            resource = ProjectFactory(creator=user)
        else:
            resource = DraftRegistrationFactory(initiator=user)
        resource.affiliated_institutions.set([active_institution, institution_to_deactivate])
        return resource

    @pytest.fixture()
    def affiliated_preprint(self, user, active_institution, institution_to_deactivate):
        preprint = PreprintFactory(creator=user)
        preprint.affiliated_institutions.set([active_institution, institution_to_deactivate])
        return preprint

    def test_include_deactivated_on_every_model(self, resource, active_institution, institution_to_deactivate):
        self._deactivate(institution_to_deactivate)
        institutions = resource.get_affiliated_institutions(include_deactivated=True)
        assert set(institutions) == {active_institution, institution_to_deactivate}

    def test_resource_excludes_deactivated_by_default(self, affiliated_preprint, active_institution, institution_to_deactivate):
        self._deactivate(institution_to_deactivate)
        assert list(affiliated_preprint.get_affiliated_institutions()) == [active_institution]

    def test_resource_include_deactivated_returns_a_queryset(self, affiliated_preprint, institution_to_deactivate):
        self._deactivate(institution_to_deactivate)
        names = affiliated_preprint.get_affiliated_institutions(include_deactivated=True).values_list('name', flat=True)
        assert institution_to_deactivate.name in names

    def test_resource_include_deactivated_is_noop_while_active(self, affiliated_preprint, active_institution, institution_to_deactivate):
        both = {active_institution, institution_to_deactivate}
        assert set(affiliated_preprint.get_affiliated_institutions()) == both
        assert set(affiliated_preprint.get_affiliated_institutions(include_deactivated=True)) == both

    def test_user_excludes_deactivated_by_default(self, user, active_institution, institution_to_deactivate):
        self._deactivate(institution_to_deactivate)
        assert list(user.get_affiliated_institutions()) == [active_institution]

    def test_user_include_deactivated(self, user, active_institution, institution_to_deactivate):
        self._deactivate(institution_to_deactivate)
        institutions = user.get_affiliated_institutions(include_deactivated=True)
        assert set(institutions) == {active_institution, institution_to_deactivate}

    def test_user_include_deactivated_returns_a_queryset(self, user, institution_to_deactivate):
        self._deactivate(institution_to_deactivate)
        names = user.get_affiliated_institutions(include_deactivated=True).values_list('name', flat=True)
        assert institution_to_deactivate.name in names

    def test_user_include_deactivated_is_noop_while_active(self, user, active_institution, institution_to_deactivate):
        both = {active_institution, institution_to_deactivate}
        assert set(user.get_affiliated_institutions()) == both
        assert set(user.get_affiliated_institutions(include_deactivated=True)) == both


@pytest.mark.django_db
class TestPreprintVersionAffiliations:
    """
    A new preprint version inherits the affiliations of the version it was created from, including
    institutions that have since been turned off, so that its metadata keeps their ROR ids
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
    def preprint(self, user, institution):
        preprint = PreprintFactory(creator=user)
        preprint.affiliated_institutions.set([institution])
        return preprint

    def test_new_version_keeps_deactivated_affiliation(self, preprint, user, institution):
        institution.deactivated = timezone.now()
        institution.save()
        new_preprint, _ = Preprint.create_version(
            create_from_guid=preprint._id,
            auth=Auth(user),
            ignore_permission=True,
        )
        assert institution in new_preprint.get_affiliated_institutions(include_deactivated=True)
        assert institution not in new_preprint.get_affiliated_institutions()
