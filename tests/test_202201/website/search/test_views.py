import mock
import pytest
from osf.models.user import Email
from osf_tests.factories import UserFactory, fake
from tests.base import OsfTestCase
from website.util import api_url_for


@pytest.mark.django_db
@pytest.mark.enable_search
class TestContributorSearch(OsfTestCase):

    def setUp(self):
        super(TestContributorSearch, self).setUp()
        self.firstname = 'jane'
        self.fullname1 = self.firstname + ' 1'
        self.fullname2 = self.firstname + ' 2'

        self.user1 = UserFactory(fullname=self.fullname1)
        self.user2 = UserFactory(fullname=self.fullname2)

        self.user1_alternate_email = 'user1@gmail.com'
        self.user1.emails.create(address=self.user1_alternate_email)
        self.user1.schools = [{
            'degree': fake.catch_phrase(),
            'institution': fake.company(),
            'department': fake.bs(),
            'startMonth': 1,
            'startYear': '2020',
            'endMonth': 1,
            'endYear': '2022',
        }]
        self.user1.jobs = [{
            'title': fake.catch_phrase(),
            'institution': fake.company(),
            'department': fake.bs(),
            'startMonth': 1,
            'startYear': '2020',
            'endMonth': 1,
            'endYear': '2022',
        }]
        self.user1.save()
        self.user2.save()

    @mock.patch('osf.models.user.OSFUser.objects.filter')
    def test_search_contributor_email_not_valid(self, mockApi):
        res = self.app.get(
            api_url_for('search_contributor'), {
                'query': 'abc@.@gmail.com',
                'page': 5,
                'size': 10},
            expect_errors=True
        )
        mockApi.assert_not_called()
        assert res.status_code == 200

    def test_search_contributor_query_set_exists(self):
        res = self.app.get(
            api_url_for('search_contributor'), {
                'query': self.user1_alternate_email,
                'page': 5,
                'size': 10
            },
            expect_errors=True
        )
        assert res.json['users'][0]['fullname'] == self.fullname1
        assert res.status_code == 200

    def test_search_contributor_user_schools(self):
        res = self.app.get(
            api_url_for('search_contributor'), {
                'query': self.user1_alternate_email,
                'page': 5,
                'size': 10
            },
            expect_errors=True
        )
        assert res.json['users'][0]['education'] == self.user1.schools[0]['institution']
        assert res.status_code == 200

    def test_search_contributor_user_jobs(self):
        res = self.app.get(
            api_url_for('search_contributor'), {
                'query': self.user1_alternate_email,
                'page': 5,
                'size': 10
            },
            expect_errors=True
        )
        assert res.json['users'][0]['employment'] == self.user1.jobs[0]['institution']
        assert res.status_code == 200

    @mock.patch('website.search.views.OSFUser.objects')
    def test_search_contributor_email_not_valid_temp(self, mockOSFUser):
        mockOSFUser.filter.return_value.filter.return_value = Email.objects.none()
        self.app.get(
            api_url_for('search_contributor'), {
                'query': self.user1_alternate_email,
                'page': 5,
                'size': 10},
            expect_errors=True
        )
        assert mockOSFUser.filter.return_value.filter.called == True

    @mock.patch('osf.models.node.AbstractNode.load')
    @mock.patch('website.search.views.OSFUser.objects')
    def test_search_contributor_exclude_is_not_none_temp(self, mockOSFUser, mockAbstractNode):
        mockOSFUser.filter.return_value.filter.return_value.exclude.return_value = Email.objects.none()
        mockAbstractNode.contributors.return_value = 'contributor'

        self.app.get(
            api_url_for('search_contributor'), {
                'query': self.user1_alternate_email,
                'page': 5,
                'size': 10,
                'excludeNode': 'excludeNode value'},
            expect_errors=True
        )
        assert mockOSFUser.filter.return_value.filter.return_value.exclude.called == True
