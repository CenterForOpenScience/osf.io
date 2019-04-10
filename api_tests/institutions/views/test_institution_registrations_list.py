from nose.tools import *  # noqa:

from tests.base import ApiTestCase
from osf_tests.factories import (
    AuthUserFactory,
    InstitutionFactory,
    RegistrationFactory,
    WithdrawnRegistrationFactory
)

from framework.auth import Auth
from api.base.settings.defaults import API_BASE
from api_tests.registrations.filters.test_filters import RegistrationListFilteringMixin
from osf.models import Node


class TestInstitutionRegistrationList(ApiTestCase):
    def setUp(self):
        super(TestInstitutionRegistrationList, self).setUp()
        self.institution = InstitutionFactory()
        self.registration1 = RegistrationFactory(is_public=True)
        self.registration1.affiliated_institutions.add(self.institution)
        self.registration1.save()
        self.user1 = AuthUserFactory()
        self.user2 = AuthUserFactory()
        self.registration2 = RegistrationFactory(
            creator=self.user1, is_public=False)
        self.registration2.affiliated_institutions.add(self.institution)
        self.registration2.add_contributor(self.user2, auth=Auth(self.user1))
        self.registration2.save()
        self.registration3 = RegistrationFactory(
            creator=self.user2, is_public=False)
        self.registration3.affiliated_institutions.add(self.institution)
        self.registration3.save()

        self.institution_node_url = '/{0}institutions/{1}/registrations/'.format(
            API_BASE, self.institution._id)

    def test_return_all_public_nodes(self):
        res = self.app.get(self.institution_node_url)

        assert_equal(res.status_code, 200)
        ids = [each['id'] for each in res.json['data']]

        assert_in(self.registration1._id, ids)
        assert_not_in(self.registration2._id, ids)
        assert_not_in(self.registration3._id, ids)

    def test_does_not_return_private_nodes_with_auth(self):
        res = self.app.get(self.institution_node_url, auth=self.user1.auth)

        assert_equal(res.status_code, 200)
        ids = [each['id'] for each in res.json['data']]

        assert_in(self.registration1._id, ids)
        assert_not_in(self.registration2._id, ids)
        assert_not_in(self.registration3._id, ids)

    def test_doesnt_return_retractions_without_auth(self):
        self.registration2.is_public = True
        self.registration2.save()
        WithdrawnRegistrationFactory(
            registration=self.registration2, user=self.user1)
        assert_true(self.registration2.is_retracted)

        res = self.app.get(self.institution_node_url)

        assert_equal(res.status_code, 200)
        ids = [each['id'] for each in res.json['data']]

        assert_not_in(self.registration2._id, ids)

    def test_doesnt_return_retractions_with_auth(self):
        WithdrawnRegistrationFactory(
            registration=self.registration2, user=self.user1)

        assert_true(self.registration2.is_retracted)

        res = self.app.get(self.institution_node_url, auth=self.user1.auth)

        assert_equal(res.status_code, 200)
        ids = [each['id'] for each in res.json['data']]

        assert_not_in(self.registration2._id, ids)

    def test_total_biographic_contributor_in_institution_registration(self):
        user3 = AuthUserFactory()
        registration3 = RegistrationFactory(is_public=True, creator=self.user1)
        registration3.affiliated_institutions.add(self.institution)
        registration3.add_contributor(self.user2, auth=Auth(self.user1))
        registration3.add_contributor(
            user3, auth=Auth(self.user1), visible=False)
        registration3.save()
        registration3_url = '/{0}registrations/{1}/?embed=contributors'.format(
            API_BASE, registration3._id)

        res = self.app.get(registration3_url)
        assert_true(
            res.json['data']['embeds']['contributors']['links']['meta']['total_bibliographic']
        )
        assert_equal(
            res.json['data']['embeds']['contributors']['links']['meta']['total_bibliographic'],
            2
        )


class TestRegistrationListFiltering(
        RegistrationListFilteringMixin,
        ApiTestCase):

    def setUp(self):
        self.institution = InstitutionFactory()
        self.url = '/{}institutions/{}/registrations/?version=2.2&'.format(
            API_BASE, self.institution._id)

        super(TestRegistrationListFiltering, self).setUp()

        A_children = [
            child for child in Node.objects.get_children(
                self.node_A
            )
        ]
        B2_children = [
            child for child in Node.objects.get_children(
                self.node_B2
            )
        ]

        for child in (A_children + B2_children):
            child.affiliated_institutions.add(self.institution)
            child.is_public = True
            child.save()

        self.node_A.is_public = True
        self.node_B2.is_public = True
        self.node_A.affiliated_institutions.add(self.institution)
        self.node_B2.affiliated_institutions.add(self.institution)

        self.node_A.save()
        self.node_B2.save()
