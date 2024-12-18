import pytest
from osf.models import Contributor, NodeLog
from osf_tests.factories import (
    AuthUserFactory,
    ProjectFactory,
    InstitutionFactory,
)
from api.base.settings.defaults import API_BASE
from rest_framework import status
from tests.utils import assert_latest_log


@pytest.mark.django_db
class TestChangeInstitutionalAdminContributor:

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def institution(self):
        return InstitutionFactory()

    @pytest.fixture()
    def institutional_admin(self, institution):
        admin_user = AuthUserFactory()
        institution.get_group('institutional_admins').user_set.add(admin_user)
        return admin_user

    @pytest.fixture()
    def project(self, user, institutional_admin):
        project = ProjectFactory(creator=user)
        project.add_contributor(institutional_admin, visible=False)
        return project

    @pytest.fixture()
    def url_contrib(self, project, user):
        return f'/{API_BASE}nodes/{project._id}/contributors/{user._id}/'

    def test_cannot_set_institutional_admin_contributor_bibliographic(self, app, user, project, institutional_admin, url_contrib):
        res = app.put_json_api(
            url_contrib,
            {
                'data': {
                    'id': f'{project._id}-{institutional_admin._id}',
                    'type': 'contributors',
                    'attributes': {
                        'bibliographic': True,
                    }
                }
            },
            auth=user.auth,
            expect_errors=True
        )
        assert res.status_code == 409
        project.reload()
        contributor = Contributor.objects.get(
            node=project,
            user=institutional_admin
        )
        assert not contributor.visible
