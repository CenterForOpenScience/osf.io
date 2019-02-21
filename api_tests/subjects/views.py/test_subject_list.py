import pytest

from django.db.models import BooleanField, Case, When

from api.base.settings.defaults import API_BASE
from osf.models import Subject
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
    def subjects(self):
        return Subject.objects.all().annotate(is_other=Case(
            When(text__istartswith='other', then=True),
            default=False,
            output_field=BooleanField()
        )).order_by('is_other', 'text')

    @pytest.fixture()
    def url_subject_list(self):
        return '/{}subjects/'.format(API_BASE)

    @pytest.fixture()
    def url_subject_detail(self, subject):
        return '/{}subjects/{}/'.format(API_BASE, subject._id)

    @pytest.fixture()
    def res_subject_list(self, app, url_subject_list):
        return app.get(url_subject_list)

    @pytest.fixture()
    def data_subject_list(self, app, res_subject_list):
        return res_subject_list.json['data']

    def test_subject_other_ordering(self, subject_other, data_subject_list):
        assert data_subject_list[-1]['id'] == subject_other._id

    def test_subject_success(
            self, subject, subject_child_one, subject_child_two,
            subjects, res_subject_list):
        # make sure there are subjects to filter through
        assert len(subjects) > 0
        assert res_subject_list.status_code == 200
        assert res_subject_list.content_type == 'application/vnd.api+json'

    def test_subject_text(self, subjects, data_subject_list):
        for index, subject in enumerate(subjects):
            if index >= len(data_subject_list):
                break  # only iterate though first page of results
            assert data_subject_list[index]['attributes']['text'] == subject.text

    def test_subject_filter_by_parent(self, app, url_subject_list, subject):
        children_subjects = Subject.objects.filter(parent__id=subject.id)
        children_url = '{}?filter[parent]={}'.format(
            url_subject_list, subject._id)

        res = app.get(children_url)
        assert res.status_code == 200

        data = res.json['data']
        assert len(children_subjects) == len(data)

        for subject_ in data:
            child = Subject.objects.get(_id=subject_['id'])
            assert child.parent == subject

    def test_get_subject_detail(self, app, url_subject_detail, subject, subject_child_one, subject_child_two):
        res = app.get(url_subject_detail + '?version=2.15')
        data = res.json['data']
        assert data['attributes']['text'] == subject.text
        assert 'children' in data['relationships']
        assert 'parent' in data['relationships']
        assert data['relationships']['parent']['data'] is None

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
