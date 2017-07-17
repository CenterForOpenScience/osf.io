import pytest

from api.base.settings.defaults import API_BASE
from osf.models import Subject
from osf_tests.factories import SubjectFactory

@pytest.mark.django_db
class TestTaxonomy:

    @pytest.fixture()
    def subject(self):
        return SubjectFactory()

    @pytest.fixture()
    def child_one_subject(self, subject):
        return SubjectFactory(parent=subject)

    @pytest.fixture()
    def child_two_subject(self, subject):
        return SubjectFactory(parent=subject)

    @pytest.fixture()
    def subjects(self):
        return Subject.objects.all()

    @pytest.fixture()
    def url_subject_list(self):
         return '/{}taxonomies/'.format(API_BASE)

    @pytest.fixture()
    def res_subject_list(self, app, url_subject_list):
        return app.get(url_subject_list)

    @pytest.fixture()
    def data_subject_list(self, app, res_subject_list):
        return res_subject_list.json['data']

    def test_taxonomy_success(self, subject,  child_one_subject, child_two_subject, subjects, res_subject_list):
        assert len(subjects) > 0  # make sure there are subjects to filter through
        assert res_subject_list.status_code == 200
        assert res_subject_list.content_type == 'application/vnd.api+json'

    def test_taxonomy_text(self, subjects, data_subject_list):
        for index, subject in enumerate(subjects):
            if index >= len(data_subject_list): break  # only iterate though first page of results
            assert data_subject_list[index]['attributes']['text'] == subject.text

    def test_taxonomy_parents(self, subjects, data_subject_list):
        for index, subject in enumerate(subjects):
            if index >= len(data_subject_list): break
            parents_ids = []
            for parent in data_subject_list[index]['attributes']['parents']:
                parents_ids.append(parent['id'])
            if subject.parent:
                assert subject.parent._id in parents_ids

    def test_taxonomy_filter_top_level(self, app, subject, child_one_subject, child_two_subject, url_subject_list):
        top_level_subjects = Subject.objects.filter(parent__isnull=True)
        top_level_url = url_subject_list + '?filter[parents]=null'

        res = app.get(top_level_url)
        assert res.status_code == 200

        data = res.json['data']
        assert len(top_level_subjects) == len(data)
        assert len(top_level_subjects) > 0
        for subject in data:
            assert subject['attributes']['parents'] == []

    def test_taxonomy_filter_by_parent(self, app, url_subject_list, subject):
        children_subjects = Subject.objects.filter(parent__id=subject.id)
        children_url = url_subject_list + '?filter[parents]={}'.format(subject._id)

        res = app.get(children_url)
        assert res.status_code == 200

        data = res.json['data']
        assert len(children_subjects) == len(data)

        for subject in data:
            parents_ids = []
            for parent in subject['attributes']['parents']:
                parents_ids.append(parent['id'])
            assert subject._id in parents_ids
