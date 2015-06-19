import mock
from nose.tools import *  # flake8: noqa

from api.base.settings.defaults import API_BASE

from tests.base import ApiTestCase, fake
from tests.factories import UserFactory, ProjectFactory, FolderFactory, RegistrationFactory, DashboardFactory, NodeFactory

class TestRegistrationList(ApiTestCase):
    def setUp(self):
        ApiTestCase.setUp(self)
        self.user = UserFactory.build()
        password = fake.password()
        self.password = password
        self.user.set_password(password)
        self.user.save()
        self.basic_auth = (self.user.username, password)

        self.user_two = UserFactory.build()
        self.user_two.set_password(password)
        self.user_two.save()
        self.basic_auth_two = (self.user_two.username, password)

        self.project = ProjectFactory(is_public=False, creator=self.user)
        self.registration_project = RegistrationFactory(creator=self.user, project=self.project)

        self.project_two = ProjectFactory(is_public=False, creator=self.user)
        self.registration_project_two = RegistrationFactory(creator=self.user, project=self.project_two)
        self.project_two.is_deleted = True
        self.registration_project_two.is_deleted = True
        self.project_two.save()
        self.registration_project_two.save()

        self.project_three = ProjectFactory(is_public=True, creator=self.user_two)
        self.registration_project_three = RegistrationFactory(creator=self.user_two, project=self.project_three)

        self.project_four = ProjectFactory(is_public=False, creator=self.user_two)
        self.registration_project_four = RegistrationFactory(creator=self.user_two, project=self.project_four)

        self.url = '/{}registrations/'.format(API_BASE)


    def test_list_all_registrations(self):
        res = self.app.get(self.url, auth=self.basic_auth)
        assert_equal(res.status_code, 200)
        ids = [each['id'] for each in res.json['data']]
        assert_in(self.registration_project._id, ids)
        assert_not_in(self.registration_project_two._id, ids)
        assert_in(self.registration_project_three._id, ids)
        assert_not_in(self.registration_project_four._id, ids)
