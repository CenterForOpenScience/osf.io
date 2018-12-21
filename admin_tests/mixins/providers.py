import pytest
import json

from osf_tests.factories import SubjectFactory
from admin.base.forms import ImportFileForm


pytestmark = pytest.mark.django_db


@pytest.mark.urls('admin.base.urls')
class ProviderListMixinBase:

    @pytest.fixture()
    def provider_factory():
        raise NotImplementedError

    @pytest.fixture()
    def provider_class():
        raise NotImplementedError

    @pytest.fixture()
    def provider_one(self, provider_factory):
        return provider_factory()

    @pytest.fixture()
    def provider_two(self, provider_factory):
        return provider_factory()

    @pytest.fixture()
    def view(self):
        raise NotImplementedError

    def test_get_list(self, req, view):
        res = view.get(req)
        assert res.status_code == 200

    def test_get_queryset(self, view, provider_one, provider_two, provider_class):
        providers_returned = list(view.get_queryset())
        assert provider_one in providers_returned
        assert provider_two in providers_returned

        assert isinstance(providers_returned[0], provider_class)

    def test_context_data(self, provider_one, provider_two, view, provider_class):
        view.object_list = view.get_queryset()
        res = view.get_context_data()
        assert isinstance(res, dict)
        assert len(res['{}_providers'.format(provider_one.readable_type)]) == 2
        assert isinstance(res['{}_providers'.format(provider_one.readable_type)][0], provider_class)


@pytest.mark.urls('admin.base.urls')
class ProcessCustomTaxonomyMixinBase:

    @pytest.fixture()
    def provider_factory():
        raise NotImplementedError

    @pytest.fixture()
    def view(self):
        raise NotImplementedError

    @pytest.fixture()
    def provider(self, provider_factory):
        return provider_factory()

    @pytest.fixture()
    def subject_one(self):
        return SubjectFactory()

    @pytest.fixture()
    def subject_one_a(self, subject_one):
        return SubjectFactory(parent=subject_one)

    @pytest.fixture()
    def subject_one_a_a(self, subject_one_a):
        return SubjectFactory(parent=subject_one_a)

    @pytest.fixture()
    def subject_two(self):
        return SubjectFactory()

    @pytest.fixture()
    def subject_two_a(self, subject_two):
        return SubjectFactory(parent=subject_two)

    @pytest.fixture()
    def subject_three(self):
        return SubjectFactory()

    @pytest.fixture()
    def subject_three_a(self, subject_three):
        return SubjectFactory(parent=subject_three)

    def test_process_taxonomy_changes_subjects(
            self, provider, view, user, req, subject_one,
            subject_one_a, subject_two, subject_two_a, subject_three_a):

        custom_taxonomy = {
            'include': [subject_one.text, subject_three_a.text],
            'exclude': [subject_one_a.text],
            'custom': {
                'Changed Subject Name': {'parent': subject_two.text, 'bepress': subject_two_a.text},
                subject_two.text: {'parent': '', 'bepress': subject_two.text}
            }
        }
        req.POST = {
            'custom_taxonomy_json': json.dumps(custom_taxonomy),
            'provider_id': provider.id
        }

        view.post(req)

        actual_provider_subjects = set(provider.subjects.all().values_list('text', flat=True))
        expected_subjects = set([subject_one.text, subject_two.text, subject_three_a.text, 'Changed Subject Name'])

        assert actual_provider_subjects == expected_subjects
        assert provider.subjects.get(text='Changed Subject Name').parent.text == subject_two.text

    def test_process_taxonomy_invalid_returns_feedback(self, req, view, provider, subject_two, subject_two_a):
        custom_taxonomy = {
            'include': [],
            'exclude': [],
            'custom': {
                'Changed Subject Name': {'parent': subject_two.text, 'bepress': subject_two_a.text},
            }
        }
        req.POST = {
            'custom_taxonomy_json': json.dumps(custom_taxonomy),
            'provider_id': provider.id
        }

        with pytest.raises(AssertionError):
            view.post(req)


@pytest.mark.urls('admin.base.urls')
class ProviderDisplayMixinBase:

    @pytest.fixture()
    def provider_factory(self):
        raise NotImplementedError

    @pytest.fixture()
    def form_class(self):
        raise NotImplementedError

    @pytest.fixture()
    def provider_class(self):
        raise NotImplementedError

    @pytest.fixture()
    def provider(self, provider_factory):
        return provider_factory()

    @pytest.fixture()
    def view(self):
        raise NotImplementedError

    def test_get_object(self, view, provider, provider_class):
        obj = view.get_object()
        assert isinstance(obj, provider_class)
        assert obj.name == provider.name

    def test_context_data(self, view, provider, provider_class, form_class):
        res = view.get_context_data()
        assert isinstance(res, dict)
        assert isinstance(res['{}_provider'.format(provider.readable_type)], dict)
        assert res['{}_provider'.format(provider.readable_type)]['name'] == provider.name

        assert isinstance(res['form'], form_class)
        assert isinstance(res['import_form'], ImportFileForm)

    def test_get(self, view, req):
        res = view.get(req)
        assert res.status_code == 200

@pytest.mark.urls('admin.base.urls')
class CreateProviderMixinBase:

    @pytest.fixture()
    def provider_factory(self):
        raise NotImplementedError

    @pytest.fixture()
    def provider(self, provider_factory):
        return provider_factory()

    @pytest.fixture()
    def view(self):
        raise NotImplementedError

    def test_get_context_data(self, view, provider):
        view.object = provider
        res = view.get_context_data()
        assert isinstance(res, dict)
        assert isinstance(res['import_form'], ImportFileForm)

    def test_get_view(self, view, req):
        res = view.get(req)
        assert res.status_code == 200


@pytest.mark.urls('admin.base.urls')
class DeleteProviderMixinBase:

    @pytest.fixture()
    def provider_factory(self):
        raise NotImplementedError

    @pytest.fixture()
    def provider(self, provider_factory):
        return provider_factory()

    @pytest.fixture()
    def view(self, req, provider):
        raise NotImplementedError

    def test_can_delete(self, req, view):
        res = view.get(req)
        assert res.status_code == 200
