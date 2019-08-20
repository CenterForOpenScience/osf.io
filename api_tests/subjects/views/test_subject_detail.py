import pytest

from api.base.settings.defaults import API_BASE
from api.taxonomies.serializers import subjects_as_relationships_version
from osf_tests.factories import SubjectFactory


@pytest.mark.django_db
class TestSubject:

    @pytest.fixture(autouse=True)
    def subject(self):
        return SubjectFactory(text='A')

    @pytest.fixture(autouse=True)
    def subject_other(self):
        return SubjectFactory(text='Other Sub')

    @pytest.fixture(autouse=True)
    def subject_a(self):
        return SubjectFactory(text='Z')

    @pytest.fixture(autouse=True)
    def subject_child_one(self, subject):
        return SubjectFactory(parent=subject)

    @pytest.fixture(autouse=True)
    def subject_child_two(self, subject):
        return SubjectFactory(parent=subject)

    @pytest.fixture()
    def url_subject_list(self):
        return '/{}subjects/'.format(API_BASE)

    @pytest.fixture()
    def url_subject_detail(self, subject):
        return '/{}subjects/{}/'.format(API_BASE, subject._id)

    def test_get_subject_detail(self, app, url_subject_detail, subject, subject_child_one, subject_child_two):
        res = app.get(url_subject_detail + '?version={}&related_counts=children'.format(subjects_as_relationships_version))
        data = res.json['data']
        assert data['attributes']['text'] == subject.text
        assert 'children' in data['relationships']
        assert 'parent' in data['relationships']
        assert data['relationships']['parent']['data'] is None
        assert data['relationships']['children']['links']['related']['meta']['count'] == 2

        # Follow children link
        children_link = data['relationships']['children']['links']['related']['href']
        res = app.get(children_link)
        data = res.json['data']

        assert len(data) == 2
        children = [child['id'] for child in data]
        assert subject_child_one._id in children
        assert subject_child_two._id in children

        # Follow child's parent link
        parent_link = data[0]['relationships']['parent']['links']['related']['href']
        res = app.get(parent_link)
        assert res.json['data']['id'] == subject._id
