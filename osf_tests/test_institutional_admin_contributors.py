import pytest
from osf.models import Contributor
from osf_tests.factories import (
    AuthUserFactory,
    ProjectFactory,
    InstitutionFactory
)
from django.db.utils import IntegrityError

@pytest.mark.django_db
class TestContributorModel:

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def project(self):
        return ProjectFactory()

    @pytest.fixture()
    def institution(self):
        return InstitutionFactory()

    @pytest.fixture()
    def institutional_admin(self, institution):
        admin_user = AuthUserFactory()
        institution.get_group('institutional_admins').user_set.add(admin_user)
        return admin_user

    def test_contributor_with_visible_and_institutional_admin_raises_error(self, institutional_admin, project, institution):
        contributor = Contributor(
            user=institutional_admin,
            node=project,
            visible=False,
        )
        contributor.save()

        contributor.visible = True

        with pytest.raises(IntegrityError, match='Curators cannot be made bibliographic contributors'):
            contributor.save()
