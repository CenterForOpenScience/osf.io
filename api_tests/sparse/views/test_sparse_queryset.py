# api_tests/sparse/views/test_views.py

from rest_framework.test import APITestCase, APIRequestFactory, force_authenticate
from api.sparse.views import SparseUserNodeList
from osf_tests.factories import AuthUserFactory, ProjectFactory, NodeLicenseRecordFactory
from django.urls import reverse

class TestSparseUserNodeList(APITestCase):

    def setUp(self):
        super().setUp()
        self.user = AuthUserFactory()
        self.other_user = AuthUserFactory()
        self.project = ProjectFactory(creator=self.user)
        self.project_license = NodeLicenseRecordFactory()
        self.project.node_license = self.project_license
        self.project.save()

        self.other_project = ProjectFactory(creator=self.other_user)

        self.factory = APIRequestFactory()
        self.view = SparseUserNodeList.as_view()

    def test_get_queryset_returns_user_nodes(self):
        # create requwat
        url = reverse('sparse:user-nodes', kwargs={'user_id': self.user._id})
        request = self.factory.get(url)
        force_authenticate(request, user=self.user)

        # get response from view
        response = self.view(request, user_id=self.user._id)

        # confirm http status code
        self.assertEqual(response.status_code, 200)

        # verify response data
        response.render()
        data = response.data

        # verify my project is included
        node_ids = [node['id'] for node in data['data']]
        self.assertIn(self.project._id, node_ids)

        # verify other user's project is not included
        self.assertNotIn(self.other_project._id, node_ids)

    def test_get_queryset_includes_related_fields(self):
        # create request
        url = reverse('sparse:user-nodes', kwargs={'user_id': self.user._id})
        request = self.factory.get(url)
        force_authenticate(request, user=self.user)

        # get response from view
        response = self.view(request, user_id=self.user._id)

        # confirm http status code
        self.assertEqual(response.status_code, 200)

        # verify response data
        response.render()
        data = response.data

        # verify node data
        for node in data['data']:
            if node['id'] == self.project._id:
                # verify creator__guids is included
                self.assertIn('creator', node['relationships'])
                self.assertIn('id', node['relationships']['creator']['data'])
                self.assertEqual(node['relationships']['creator']['data']['id'], self.user._id)

                # verify node_license is included
                self.assertIn('node_license', node['attributes'])
                self.assertEqual(node['attributes']['node_license']['id'], self.project_license.node_license._id)

                # verify root__guids is included
                self.assertIn('root', node['relationships'])
                self.assertIn('id', node['relationships']['root']['data'])
                self.assertEqual(node['relationships']['root']['data']['id'], self.project.root._id)
