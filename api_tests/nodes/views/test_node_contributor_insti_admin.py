import pytest
from osf.models import Contributor
from osf_tests.factories import (
    AuthUserFactory,
    ProjectFactory,
    InstitutionFactory,
)
from api.base.settings.defaults import API_BASE


@pytest.mark.django_db
class TestChangeInstitutionalAdminContributor:

    @pytest.fixture()
    def project_admin(self):
        return AuthUserFactory()

    @pytest.fixture()
    def project_admin2(self):
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
    def project(self, project_admin, project_admin2, institutional_admin):
        project = ProjectFactory(creator=project_admin)
        project.add_contributor(project_admin2, permissions='admin', visible=False)
        project.add_contributor(institutional_admin, visible=False)
        return project

    @pytest.fixture()
    def url_contrib(self, project, institutional_admin):
        return f'/{API_BASE}nodes/{project._id}/contributors/{institutional_admin._id}/'

    def test_cannot_set_institutional_admin_contributor_bibliographic(self, app, project_admin, project,
                                                                      institutional_admin, url_contrib):
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
            auth=project_admin.auth,
            expect_errors=True
        )

        assert res.status_code == 409
        assert res.json['errors'][0]['detail'] == 'Curators cannot be made bibliographic contributors'

        contributor = Contributor.objects.get(
            node=project,
            user=institutional_admin
        )
        assert not contributor.visible
