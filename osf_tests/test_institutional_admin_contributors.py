import pytest
from django.core.exceptions import ValidationError
from osf.models import Contributor, Institution
from osf_tests.factories import AuthUserFactory, ProjectFactory, InstitutionFactory
from django.db.utils import IntegrityError

@pytest.mark.django_db
class TestContributorModel:

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def project(self, user):
        return ProjectFactory(creator=user)

    @pytest.fixture()
    def institution(self):
        return InstitutionFactory()

    def test_contributor_with_visible_and_institutional_admin_raises_error(self, user, project, institution):
        contributor = Contributor(
            user=user,
            node=project,
            visible=True,
            institutional_admin=institution
        )
        with pytest.raises(IntegrityError, match='new row for relation "osf_contributor" violates check constraint "no_visible_with_institutional_admin"'):
            contributor.save()  # Use clean() for validation logic

    def test_contributor_with_visible_but_no_institutional_admin(self, user, project):
        # Ensure no duplicate contributor exists
        Contributor.objects.filter(user=user, node=project).delete()

        contributor = Contributor(
            user=user,
            node=project,
            visible=True,
            institutional_admin=None
        )
        # This should not raise an error
        contributor.save()

    def test_contributor_with_institutional_admin_but_not_visible(self, user, project, institution):
        # Ensure no duplicate contributor exists
        Contributor.objects.filter(user=user, node=project).delete()

        contributor = Contributor(
            user=user,
            node=project,
            visible=False,
            institutional_admin=institution
        )
        # This should not raise an error
        contributor.save()

    def test_database_constraint_no_visible_with_institutional_admin(self, user, project, institution):
        # Ensure no duplicate contributor exists
        Contributor.objects.filter(user=user, node=project).delete()

        Contributor.objects.create(
            user=user,
            node=project,
            visible=False,
            institutional_admin=institution
        )  # Should succeed

        with pytest.raises(Exception):  # Check database constraint
            Contributor.objects.create(
                user=user,
                node=project,
                visible=True,
                institutional_admin=institution
            )
