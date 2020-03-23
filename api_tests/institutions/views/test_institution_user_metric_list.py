import pytest
import datetime

from api.base.settings.defaults import API_BASE
from osf_tests.factories import (
    InstitutionFactory,
    AuthUserFactory,
)

from osf.metrics import UserInstitutionProjectCounts

@pytest.mark.es
@pytest.mark.django_db
class TestInstitutionUserMetricList:

    @pytest.fixture()
    def institution(self):
        return InstitutionFactory()

    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def user2(self):
        return AuthUserFactory()

    @pytest.fixture()
    def admin(self, institution):
        user = AuthUserFactory()
        group = institution.get_group('institutional_admins')
        group.user_set.add(user)
        group.save()
        return user

    @pytest.fixture()
    def url(self, institution):
        return f'/{API_BASE}institutions/{institution._id}/user_metrics/'

    def test_get(self, app, url, user, user2, admin, institution):

        resp = app.get(url, expect_errors=True)
        assert resp.status_code == 401

        resp = app.get(url, auth=user.auth, expect_errors=True)
        assert resp.status_code == 403

        resp = app.get(url, auth=admin.auth)
        assert resp.status_code == 200

        assert resp.json['data'] == []

        # Old data that shouldn't appear in responses
        UserInstitutionProjectCounts.record(
            user_id=user._id,
            institution_id=institution._id,
            department='Biology dept',
            public_project_count=4,
            private_project_count=4,
            timestamp=datetime.date(2019, 6, 4)
        ).save()

        # New data
        UserInstitutionProjectCounts.record(
            user_id=user._id,
            institution_id=institution._id,
            department='Biology dept',
            public_project_count=6,
            private_project_count=5,
        ).save()

        UserInstitutionProjectCounts.record(
            user_id=user2._id,
            institution_id=institution._id,
            department='Psychology dept',
            public_project_count=3,
            private_project_count=2,
        ).save()

        import time
        time.sleep(2)

        resp = app.get(url, auth=admin.auth)

        assert resp.json['data'] == [
            {
                'id': institution._id,
                'type': 'institution_users',
                'attributes': {
                    'user_id': user._id,
                    'user': f'({user._id}) {user.fullname}',
                    'public_projects': 6,
                    'private_projects': 5,
                    'department': 'Biology dept'
                },
                'relationships': {
                    'users': {
                        'links': {
                            'related': {
                                'href': f'http://localhost:8000/v2/users/{user._id}/',
                                'meta': {}
                            }
                        },
                        'data': {
                            'id': user._id,
                            'type': 'users'
                        }
                    },
                    'institution': {
                        'links': {
                            'related': {
                                'href': f'http://localhost:8000/v2/institutions/{institution._id}/',
                                'meta': {}
                            }
                        },
                        'data': {
                            'id': institution._id,
                            'type': 'institutions'
                        }
                    }
                },
                'links': {
                    'self': f'http://localhost:8000/v2/institutions/{institution._id}/user_metrics/'
                }
            },
            {
                'id': institution._id,
                'type': 'institution_users',
                'attributes': {
                    'user_id': user2._id,
                    'user': f'({user2._id}) {user2.fullname}',
                    'public_projects': 3,
                    'private_projects': 2,
                    'department': 'Psychology dept'
                },
                'relationships': {
                    'users': {
                        'links': {
                            'related': {
                                'href': f'http://localhost:8000/v2/users/{user2._id}/',
                                'meta': {}
                            }
                        },
                        'data': {
                            'id': user2._id,
                            'type': 'users'
                        }
                    },
                    'institution': {
                        'links': {
                            'related': {
                                'href': f'http://localhost:8000/v2/institutions/{institution._id}/',
                                'meta': {}
                            }
                        },
                        'data': {
                            'id': institution._id,
                            'type': 'institutions'
                        }
                    }
                },
                'links': {
                    'self': f'http://localhost:8000/v2/institutions/{institution._id}/user_metrics/'
                }
            }
        ]
