from nose.tools import *

from tests.base import ApiTestCase
from tests.factories import InstitutionFactory, AuthUserFactory, RegistrationFactory, RetractedRegistrationFactory

from framework.auth import Auth
from api.base.settings.defaults import API_BASE

class TestInstitutionRegistrationList(ApiTestCase):
    def setUp(self):
        super(TestInstitutionRegistrationList, self).setUp()
        self.institution = InstitutionFactory()
        self.registration1 = RegistrationFactory(is_public=True, is_registration=True)
        self.registration1.affiliated_institutions.append(self.institution)
        self.registration1.save()
        self.user1 = AuthUserFactory()
        self.user2 = AuthUserFactory()
        self.registration2 = RegistrationFactory(creator=self.user1, is_public=False, is_registration=True)
        self.registration2.affiliated_institutions.append(self.institution)
        self.registration2.add_contributor(self.user2, auth=Auth(self.user1))
        self.registration2.save()
        self.registration3 = RegistrationFactory(creator=self.user2, is_public=False, is_registration=True)
        self.registration3.affiliated_institutions.append(self.institution)
        self.registration3.save()

        self.institution_node_url = '/{0}institutions/{1}/registrations/'.format(API_BASE, self.institution._id)

    def test_return_all_public_nodes(self):
        res = self.app.get(self.institution_node_url)

        assert_equal(res.status_code, 200)
        ids = [each['id'] for each in res.json['data']]

        assert_in(self.registration1._id, ids)
        assert_not_in(self.registration2._id, ids)
        assert_not_in(self.registration3._id, ids)

    def test_return_private_nodes_with_auth(self):
        res = self.app.get(self.institution_node_url, auth=self.user1.auth)

        assert_equal(res.status_code, 200)
        ids = [each['id'] for each in res.json['data']]

        assert_in(self.registration1._id, ids)
        assert_in(self.registration2._id, ids)
        assert_not_in(self.registration3._id, ids)

    def test_return_private_nodes_mixed_auth(self):
        res = self.app.get(self.institution_node_url, auth=self.user2.auth)

        assert_equal(res.status_code, 200)
        ids = [each['id'] for each in res.json['data']]

        assert_in(self.registration1._id, ids)
        assert_in(self.registration2._id, ids)
        assert_in(self.registration3._id, ids)

    def test_doesnt_return_retractions_without_auth(self):
        self.registration2.is_public = True
        self.registration2.save()
        retraction = RetractedRegistrationFactory(registration=self.registration2, user=self.user1)
        assert_true(self.registration2.is_retracted)

        res = self.app.get(self.institution_node_url)

        assert_equal(res.status_code, 200)
        ids = [each['id'] for each in res.json['data']]

        assert_not_in(self.registration2._id, ids)

    def test_doesnt_return_retractions_with_auth(self):
        retraction = RetractedRegistrationFactory(registration=self.registration2, user=self.user1)

        assert_true(self.registration2.is_retracted)

        res = self.app.get(self.institution_node_url, auth=self.user1.auth)

        assert_equal(res.status_code, 200)
        ids = [each['id'] for each in res.json['data']]

        assert_not_in(self.registration2._id, ids)
