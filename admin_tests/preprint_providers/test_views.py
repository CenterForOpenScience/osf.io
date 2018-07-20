import json
from io import StringIO

import mock
from nose import tools as nt
from django.test import RequestFactory
from django.core.files.uploadedfile import InMemoryUploadedFile
from scripts.update_taxonomies import update_taxonomies

from tests.base import AdminTestCase
from osf_tests.factories import (
    AuthUserFactory,
    PreprintProviderFactory,
    PreprintFactory,
    SubjectFactory,
)
from osf.models import PreprintProvider, NodeLicense
from admin_tests.utilities import setup_form_view, setup_user_view
from admin.preprint_providers import views
from admin.preprint_providers.forms import PreprintProviderForm
from admin.base.forms import ImportFileForm


class TestPreprintProviderList(AdminTestCase):
    def setUp(self):
        super(TestPreprintProviderList, self).setUp()

        self.provider1 = PreprintProviderFactory()
        self.provider2 = PreprintProviderFactory()

        self.user = AuthUserFactory()

        self.request = RequestFactory().get('/fake_path')
        self.view = views.PreprintProviderList()
        self.view = setup_user_view(self.view, self.request, user=self.user)

    def test_get_list(self, *args, **kwargs):
        res = self.view.get(self.request, *args, **kwargs)
        nt.assert_equal(res.status_code, 200)

    def test_get_queryset(self):
        providers_returned = list(self.view.get_queryset())
        provider_list = [self.provider1, self.provider2]
        nt.assert_items_equal(providers_returned, provider_list)
        nt.assert_is_instance(providers_returned[0], PreprintProvider)

    def test_context_data(self):
        self.view.object_list = self.view.get_queryset()
        res = self.view.get_context_data()
        nt.assert_is_instance(res, dict)
        nt.assert_equal(len(res['preprint_providers']), 2)
        nt.assert_is_instance(res['preprint_providers'][0], PreprintProvider)


class TestPreprintProviderDisplay(AdminTestCase):
    def setUp(self):
        super(TestPreprintProviderDisplay, self).setUp()

        self.user = AuthUserFactory()

        self.preprint_provider = PreprintProviderFactory()

        self.request = RequestFactory().get('/fake_path')
        self.view = views.PreprintProviderDisplay()
        self.view = setup_user_view(self.view, self.request, user=self.user)

        self.view.kwargs = {'preprint_provider_id': self.preprint_provider.id}

    def test_get_object(self):
        obj = self.view.get_object()
        nt.assert_is_instance(obj, PreprintProvider)
        nt.assert_equal(obj.name, self.preprint_provider.name)

    def test_context_data(self):
        res = self.view.get_context_data()
        nt.assert_is_instance(res, dict)
        nt.assert_is_instance(res['preprint_provider'], dict)
        nt.assert_equal(res['preprint_provider']['name'], self.preprint_provider.name)
        nt.assert_is_instance(res['form'], PreprintProviderForm)
        nt.assert_is_instance(res['import_form'], ImportFileForm)

    def test_get(self, *args, **kwargs):
        res = self.view.get(self.request, *args, **kwargs)
        nt.assert_equal(res.status_code, 200)


class TestDeletePreprintProvider(AdminTestCase):
    def setUp(self):
        super(TestDeletePreprintProvider, self).setUp()

        self.user = AuthUserFactory()
        self.preprint_provider = PreprintProviderFactory()

        self.request = RequestFactory().get('/fake_path')
        self.view = views.DeletePreprintProvider()
        self.view = setup_user_view(self.view, self.request, user=self.user)

        self.view.kwargs = {'preprint_provider_id': self.preprint_provider.id}

    def test_cannot_delete_if_preprints_present(self):
        preprint = PreprintFactory()
        self.preprint_provider.preprint_services.add(preprint)
        self.preprint_provider.save()

        redirect = self.view.delete(self.request)
        nt.assert_equal(redirect.url, '/preprint_providers/{}/cannot_delete/'.format(self.preprint_provider.id))
        nt.assert_equal(redirect.status_code, 302)

    def test_delete_provider_with_no_preprints(self):
        redirect = self.view.delete(self.request)
        nt.assert_equal(redirect.url, '/preprint_providers/')
        nt.assert_equal(redirect.status_code, 302)

    def test_get_with_no_preprints(self):
        res = self.view.get(self.request)
        nt.assert_equal(res.status_code, 200)

    def test_cannot_get_if_preprints_present(self):
        preprint = PreprintFactory()
        self.preprint_provider.preprint_services.add(preprint)
        self.preprint_provider.save()

        redirect = self.view.get(self.request)
        nt.assert_equal(redirect.url, '/preprint_providers/{}/cannot_delete/'.format(self.preprint_provider.id))
        nt.assert_equal(redirect.status_code, 302)


class TestPreprintProviderChangeForm(AdminTestCase):
    def setUp(self):
        super(TestPreprintProviderChangeForm, self).setUp()

        self.user = AuthUserFactory()
        self.preprint_provider = PreprintProviderFactory()

        self.request = RequestFactory().get('/fake_path')
        self.request.user = self.user
        self.view = views.PreprintProviderChangeForm()
        self.view = setup_form_view(self.view, self.request, form=PreprintProviderForm())

        self.parent_1 = SubjectFactory(provider=PreprintProviderFactory(_id='osf'))
        self.child_1 = SubjectFactory(parent=self.parent_1)
        self.child_2 = SubjectFactory(parent=self.parent_1)
        self.grandchild_1 = SubjectFactory(parent=self.child_1)

        self.view.kwargs = {'preprint_provider_id': self.preprint_provider.id}

    def test_get_context_data(self):
        self.view.object = self.preprint_provider
        res = self.view.get_context_data()
        nt.assert_is_instance(res, dict)
        nt.assert_is_instance(res['import_form'], ImportFileForm)

    def test_preprint_provider_form(self):
        formatted_rule = [[[self.parent_1._id], True]]

        new_data = {
            '_id': 'newname',
            'name': 'New Name',
            'share_publish_type': 'Preprint',
            'subjects_chosen': '{}, {}, {}, {}'.format(
                self.parent_1.id, self.child_1.id, self.child_2.id, self.grandchild_1.id
            ),
            'type': 'osf.preprintprovider',
            'toplevel_subjects': [self.parent_1.id],
            'subjects_acceptable': '[]',
            'preprint_word': 'preprint'
        }
        form = PreprintProviderForm(data=new_data)
        nt.assert_true(form.is_valid())

        new_provider = form.save()
        nt.assert_equal(new_provider.name, new_data['name'])
        nt.assert_equal(new_provider.subjects_acceptable, formatted_rule)

    def test_html_fields_are_stripped(self):
        new_data = {
            '_id': 'newname',
            'name': 'New Name',
            'share_publish_type': 'Preprint',
            'subjects_chosen': '{}, {}, {}, {}'.format(
                self.parent_1.id, self.child_1.id, self.child_2.id, self.grandchild_1.id
            ),
            'type': 'osf.preprintprovider',
            'toplevel_subjects': [self.parent_1.id],
            'subjects_acceptable': '[]',
            'advisory_board': '<div><ul><li>Bill<i class="fa fa-twitter"></i> Nye</li></ul></div>',
            'description': '<span>Open Preprints <code>Open</code> Science<script></script></span>',
            'footer_links': '<p>Xiv: <script>Support</script> | <pre>Contact<pre> | <a href=""><span class="fa fa-facebook"></span></a></p>',
            'preprint_word': 'preprint'
        }

        stripped_advisory_board = '<div><ul><li>Bill Nye</li></ul></div>'
        stripped_description = '<span>Open Preprints Open Science</span>'
        stripped_footer_links = '<p>Xiv: Support | </p>Contact | <a href=""><span class="fa fa-facebook"></span></a><p></p>'

        form = PreprintProviderForm(data=new_data)
        nt.assert_true(form.is_valid())

        new_provider = form.save()
        nt.assert_equal(new_provider.name, new_data['name'])
        nt.assert_equal(new_provider.description, stripped_description)
        nt.assert_equal(new_provider.footer_links, stripped_footer_links)
        nt.assert_equal(new_provider.advisory_board, stripped_advisory_board)


class TestPreprintProviderExportImport(AdminTestCase):
    def setUp(self):
        super(TestPreprintProviderExportImport, self).setUp()

        self.user = AuthUserFactory()
        self.preprint_provider = PreprintProviderFactory()

        self.request = RequestFactory().get('/fake_path')
        self.view = views.ExportPreprintProvider()
        self.view = setup_user_view(self.view, self.request, user=self.user)

        self.view.kwargs = {'preprint_provider_id': self.preprint_provider.id}

        self.import_request = RequestFactory().get('/fake_path')
        self.import_view = views.ImportPreprintProvider()
        self.import_view = setup_user_view(self.import_view, self.import_request, user=self.user)

        self.preprint_provider.licenses_acceptable = [NodeLicense.objects.get(license_id='NONE')]
        self.subject = SubjectFactory(provider=self.preprint_provider)

    def test_post(self):
        res = self.view.get(self.request)
        content_dict = json.loads(res.content)
        nt.assert_equal(content_dict['fields']['type'], 'osf.preprintprovider')
        nt.assert_equal(content_dict['fields']['name'], self.preprint_provider.name)
        nt.assert_equal(res.__getitem__('content-type'), 'text/json')

    def test_certain_fields_not_included(self):
        res = self.view.get(self.request)
        content_dict = json.loads(res.content)
        for field in views.FIELDS_TO_NOT_IMPORT_EXPORT:
            nt.assert_not_in(field, content_dict['fields'].keys())

    def test_export_to_import_new_provider(self):
        update_taxonomies('test_bepress_taxonomy.json')

        res = self.view.get(self.request)
        content_dict = json.loads(res.content)

        content_dict['fields']['_id'] = 'new_id'
        content_dict['fields']['name'] = 'Awesome New Name'
        data = StringIO(unicode(json.dumps(content_dict), 'utf-8'))
        self.import_request.FILES['file'] = InMemoryUploadedFile(data, None, 'data', 'application/json', 500, None, {})

        res = self.import_view.post(self.import_request)

        provider_id = ''.join([i for i in res.url if i.isdigit()])
        new_provider = PreprintProvider.objects.get(id=provider_id)

        nt.assert_equal(res.status_code, 302)
        nt.assert_equal(new_provider._id, 'new_id')
        nt.assert_equal(new_provider.name, 'Awesome New Name')
        nt.assert_equal(new_provider.subjects.all().count(), 1)
        nt.assert_equal(new_provider.licenses_acceptable.all().count(), 1)
        nt.assert_equal(new_provider.subjects.all()[0].text, self.subject.text)
        nt.assert_equal(new_provider.licenses_acceptable.all()[0].license_id, 'NONE')

    def test_export_to_import_new_provider_with_models_out_of_sync(self):
        update_taxonomies('test_bepress_taxonomy.json')

        res = self.view.get(self.request)
        content_dict = json.loads(res.content)

        content_dict['fields']['_id'] = 'new_id'
        content_dict['fields']['name'] = 'Awesome New Name'
        content_dict['fields']['new_field'] = 'this is a new field, not in the model'
        del content_dict['fields']['description']  # this is a old field, removed from the model JSON

        data = StringIO(unicode(json.dumps(content_dict), 'utf-8'))
        self.import_request.FILES['file'] = InMemoryUploadedFile(data, None, 'data', 'application/json', 500, None, {})

        res = self.import_view.post(self.import_request)

        provider_id = ''.join([i for i in res.url if i.isdigit()])
        new_provider = PreprintProvider.objects.get(id=provider_id)

        nt.assert_equal(res.status_code, 302)
        nt.assert_equal(new_provider._id, 'new_id')
        nt.assert_equal(new_provider.name, 'Awesome New Name')

    def test_update_provider_existing_subjects(self):
        # If there are existing subjects for a provider, imported subjects are ignored
        self.import_view.kwargs = {'preprint_provider_id': self.preprint_provider.id}

        res = self.view.get(self.request)
        content_dict = json.loads(res.content)

        new_subject_data = {'include': [], 'exclude': []}
        new_subject_data['custom'] = {
            'TestSubject1': {
                'parent': '',
                'bepress': 'Law'
            }
        }

        content_dict['fields']['subjects'] = json.dumps(new_subject_data)
        content_dict['fields']['licenses_acceptable'] = ['CCBY']
        data = StringIO(unicode(json.dumps(content_dict), 'utf-8'))
        self.import_request.FILES['file'] = InMemoryUploadedFile(data, None, 'data', 'application/json', 500, None, {})

        res = self.import_view.post(self.import_request)

        new_provider_id = int(''.join([i for i in res.url if i.isdigit()]))

        nt.assert_equal(res.status_code, 302)
        nt.assert_equal(new_provider_id, self.preprint_provider.id)
        nt.assert_equal(self.preprint_provider.subjects.all().count(), 1)
        nt.assert_equal(self.preprint_provider.licenses_acceptable.all().count(), 1)
        nt.assert_equal(self.preprint_provider.subjects.all()[0].text, self.subject.text)
        nt.assert_equal(self.preprint_provider.licenses_acceptable.all()[0].license_id, 'CCBY')


class TestCreatePreprintProvider(AdminTestCase):
    def setUp(self):
        super(TestCreatePreprintProvider, self).setUp()

        self.user = AuthUserFactory()
        self.preprint_provider = PreprintProviderFactory()

        self.request = RequestFactory().get('/fake_path')
        self.request.user = self.user
        self.view = views.CreatePreprintProvider()
        self.view = setup_form_view(self.view, self.request, form=PreprintProviderForm())

        self.view.kwargs = {'preprint_provider_id': self.preprint_provider.id}

    def test_get_context_data(self):
        self.view.object = self.preprint_provider
        res = self.view.get_context_data()
        nt.assert_is_instance(res, dict)
        nt.assert_is_instance(res['import_form'], ImportFileForm)

    def test_get_view(self):
        res = self.view.get(self.request)
        nt.assert_equal(res.status_code, 200)


class TestGetSubjectDescendants(AdminTestCase):
    def setUp(self):
        super(TestGetSubjectDescendants, self).setUp()

        self.user = AuthUserFactory()
        self.preprint_provider = PreprintProviderFactory()

        self.parent_1 = SubjectFactory()
        self.child_1 = SubjectFactory(parent=self.parent_1)
        self.child_2 = SubjectFactory(parent=self.parent_1)
        self.grandchild_1 = SubjectFactory(parent=self.child_1)

        self.request = RequestFactory().get('/?parent_id={}'.format(self.parent_1.id))
        self.view = views.GetSubjectDescendants()
        self.view = setup_user_view(self.view, self.request, user=self.user)

    def test_get_subject_descendants(self):
        res = self.view.get(self.request)
        nt.assert_equal(res.status_code, 200)
        nt.assert_equal(res.__getitem__('content-type'), 'application/json')

        content_dict = json.loads(res.content)
        nt.assert_items_equal(
            content_dict['all_descendants'],
            [self.child_1.id, self.child_2.id, self.grandchild_1.id]
        )


class TestProcessCustomTaxonomy(AdminTestCase):
    def setUp(self):

        self.user = AuthUserFactory()

        self.subject1 = SubjectFactory()
        self.subject2 = SubjectFactory()
        self.subject3 = SubjectFactory()

        self.subject1_1 = SubjectFactory(parent=self.subject1)
        self.subject2_1 = SubjectFactory(parent=self.subject2)
        self.subject3_1 = SubjectFactory(parent=self.subject3)

        self.subject1_1_1 = SubjectFactory(parent=self.subject1_1)

        self.preprint_provider = PreprintProviderFactory()
        self.request = RequestFactory().get('/fake_path')
        self.view = views.ProcessCustomTaxonomy()
        self.view = setup_user_view(self.view, self.request, user=self.user)

    def test_process_taxonomy_changes_subjects(self):
        custom_taxonomy = {
            'include': [self.subject1.text, self.subject3_1.text],
            'exclude': [self.subject1_1.text],
            'custom': {
                'Changed Subject Name': {'parent': self.subject2.text, 'bepress': self.subject2_1.text},
                self.subject2.text: {'parent': '', 'bepress': self.subject2.text}
            }
        }
        self.request.POST = {
            'custom_taxonomy_json': json.dumps(custom_taxonomy),
            'provider_id': self.preprint_provider.id
        }

        self.view.post(self.request)

        actual_preprint_provider_subjects = self.preprint_provider.subjects.all().values_list('text', flat=True)
        expected_subjects = [self.subject1.text, self.subject2.text, self.subject3_1.text, 'Changed Subject Name']

        nt.assert_items_equal(actual_preprint_provider_subjects, expected_subjects)
        assert self.preprint_provider.subjects.get(text='Changed Subject Name').parent.text == self.subject2.text

    def test_process_taxonomy_invalid_returns_feedback(self):
        custom_taxonomy = {
            'include': [],
            'exclude': [],
            'custom': {
                'Changed Subject Name': {'parent': self.subject2.text, 'bepress': self.subject2_1.text},
            }
        }
        self.request.POST = {
            'custom_taxonomy_json': json.dumps(custom_taxonomy),
            'provider_id': self.preprint_provider.id
        }

        with nt.assert_raises(AssertionError):
            self.view.post(self.request)


class TestShareSourcePreprintProvider(AdminTestCase):
    def setUp(self):
        self.user = AuthUserFactory()
        self.user.is_superuser = True
        self.user.save()

        self.preprint_provider = PreprintProviderFactory()

        self.request = RequestFactory().get('/fake_path')
        self.view = views.ShareSourcePreprintProvider()
        self.view = setup_user_view(self.view, self.request, user=self.user)
        self.view.kwargs = {'preprint_provider_id': self.preprint_provider.id}

    @mock.patch.object(views.ShareSourcePreprintProvider, 'share_post')
    def test_update_share_token_and_source(self, share_resp):
        token = 'tokennethbranagh'
        label = 'sir'
        share_resp.return_value = {
            'included': [{
                'attributes': {
                    'token': token,
                },
                'type': 'ShareUser',
            }, {
                'attributes': {
                    'label': label
                },
                'type': 'SourceConfig',
            }]
        }

        self.view.get(self.request)
        self.preprint_provider.refresh_from_db()

        assert self.preprint_provider.access_token == token
        assert self.preprint_provider.share_source == label
