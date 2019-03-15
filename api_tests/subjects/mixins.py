# -*- coding: utf-8 -*-
import pytest

from api.base.settings.defaults import API_BASE
from osf.models import Preprint
from osf_tests.factories import (
    AuthUserFactory,
    SubjectFactory,
)


@pytest.mark.django_db
class TestUpdateSubjectsMixin(object):
    @pytest.fixture()
    def user_admin_contrib(self):
        return AuthUserFactory()

    @pytest.fixture()
    def user_non_contrib(self):
        return AuthUserFactory()

    @pytest.fixture()
    def user_write_contrib(self):
        return AuthUserFactory()

    @pytest.fixture()
    def user_read_contrib(self):
        return AuthUserFactory()

    @pytest.fixture()
    def resource(self, user_admin_contrib, user_write_contrib, user_read_contrib):
        # Return a project, preprint, collection, etc., with the appropriate
        # contributors already added
        raise NotImplementedError()

    @pytest.fixture()
    def write_can_edit(self, resource):
        # Write users can edit preprint subjects; all other models require admin
        return isinstance(resource, Preprint)

    @pytest.fixture()
    def resource_type_plural(self, resource):
        return '{}s'.format(resource.__class__.__name__.lower())

    @pytest.fixture()
    def url(self, resource, resource_type_plural):
        return '/{}{}/{}/'.format(API_BASE, resource_type_plural, resource._id)

    @pytest.fixture()
    def make_resource_payload(self):
        def payload(resource, resource_type_plural, attributes=None, relationships=None):
            payload_data = {
                'data': {
                    'id': resource._id,
                    'type': resource_type_plural,
                }
            }

            if attributes:
                payload_data['data']['attributes'] = attributes

            if relationships:
                payload_data['data']['relationships'] = relationships

            return payload_data
        return payload

    @pytest.fixture()
    def subject(self):
        return SubjectFactory()

    def test_set_subjects_as_attributes_perms(self, app, user_admin_contrib, resource, subject, resource_type_plural,
            url, make_resource_payload, user_write_contrib, user_read_contrib, user_non_contrib, write_can_edit):

        update_subjects_payload = make_resource_payload(resource, resource_type_plural, attributes={'subjects': [[subject._id]]})
        assert not resource.subjects.filter(_id=subject._id).exists()

        # test_non_authenticated_cannot_set_subjects
        res = app.patch_json_api(url, update_subjects_payload, expect_errors=True)
        assert res.status_code == 401
        assert not resource.subjects.filter(_id=subject._id).exists()

        # test_non_contrib_cannot_set_subjects
        res = app.patch_json_api(url, update_subjects_payload, auth=user_non_contrib.auth, expect_errors=True)
        assert res.status_code == 403
        assert not resource.subjects.filter(_id=subject._id).exists()

        # test_read_contrib_cannot_set_subjects
        res = app.patch_json_api(url, update_subjects_payload, auth=user_read_contrib.auth, expect_errors=True)
        assert res.status_code == 403
        assert not resource.subjects.filter(_id=subject._id).exists()

        # test_write_contrib_cannot_set_subjects_on_certain_models
        res = app.patch_json_api(url, update_subjects_payload, auth=user_write_contrib.auth, expect_errors=True)
        if write_can_edit:
            assert res.status_code == 200
            assert resource.subjects.filter(_id=subject._id).exists()
        else:
            assert res.status_code == 403
            assert not resource.subjects.filter(_id=subject._id).exists()

        # test_admin_can_set_subjects
        resource.subjects.clear()
        res = app.patch_json_api(url, update_subjects_payload, auth=user_admin_contrib.auth, expect_errors=True)
        assert res.status_code == 200
        assert resource.subjects.filter(_id=subject._id).exists()

    def test_set_subjects_as_relationships_perms(self, app, user_admin_contrib, resource, subject, resource_type_plural,
            url, make_resource_payload, user_write_contrib, user_read_contrib, user_non_contrib, write_can_edit):

        url = '{}?version=2.15'.format(url)
        update_subjects_payload = make_resource_payload(resource, resource_type_plural, relationships={
            'subjects': {
                'data': [
                    {'id': subject._id, 'type': 'subjects'}
                ]
            }
        })
        assert not resource.subjects.filter(_id=subject._id).exists()

        # test_non_authenticated_cannot_set_subjects
        res = app.patch_json_api(url, update_subjects_payload, expect_errors=True)
        assert res.status_code == 401
        assert not resource.subjects.filter(_id=subject._id).exists()

        # test_non_contrib_cannot_set_subjects
        res = app.patch_json_api(url, update_subjects_payload, auth=user_non_contrib.auth, expect_errors=True)
        assert res.status_code == 403
        assert not resource.subjects.filter(_id=subject._id).exists()

        # test_read_contrib_cannot_set_subjects
        res = app.patch_json_api(url, update_subjects_payload, auth=user_read_contrib.auth, expect_errors=True)
        assert res.status_code == 403
        assert not resource.subjects.filter(_id=subject._id).exists()

        # test_write_contrib_cannot_set_subjects_on_certain_models
        res = app.patch_json_api(url, update_subjects_payload, auth=user_write_contrib.auth, expect_errors=True)
        if write_can_edit:
            assert res.status_code == 200
            assert resource.subjects.filter(_id=subject._id).exists()
            resource.subjects.clear()
        else:
            assert res.status_code == 403
            assert not resource.subjects.filter(_id=subject._id).exists()

        # test_admin_can_set_subjects
        res = app.patch_json_api(url, update_subjects_payload, auth=user_admin_contrib.auth, expect_errors=True)
        assert res.status_code == 200
        assert resource.subjects.filter(_id=subject._id).exists()

    def test_set_subjects_as_attributes_validation(self, app, user_admin_contrib, resource, subject, resource_type_plural,
            url, make_resource_payload):

        grandparent = SubjectFactory()
        parent = SubjectFactory(parent=grandparent)
        subject.parent = parent
        subject.save()

        # test_not_list
        update_subjects_payload = make_resource_payload(resource, resource_type_plural, attributes={'subjects': grandparent._id})
        res = app.patch_json_api(url, update_subjects_payload, auth=user_admin_contrib.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Subjects are improperly formatted. Expecting list of lists.'

        # test_not_list_of_lists
        update_subjects_payload = make_resource_payload(resource, resource_type_plural, attributes={'subjects': [grandparent._id]})
        res = app.patch_json_api(url, update_subjects_payload, auth=user_admin_contrib.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Subjects are improperly formatted. Expecting list of lists.'

        # test_invalid_subject_in_payload
        update_subjects_payload = make_resource_payload(resource, resource_type_plural, attributes={'subjects': [['bad_id']]})
        res = app.patch_json_api(url, update_subjects_payload, auth=user_admin_contrib.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Subject with id <bad_id> could not be found.'

        # test_invalid_hierarchy
        update_subjects_payload = make_resource_payload(resource, resource_type_plural, attributes={'subjects': [[grandparent._id, 'bad_id']]})
        res = app.patch_json_api(url, update_subjects_payload, auth=user_admin_contrib.auth, expect_errors=True)
        assert res.status_code == 400
        assert 'Invalid subject hierarchy' in res.json['errors'][0]['detail']

        # test_full_hierarchy_not_present
        update_subjects_payload = make_resource_payload(resource, resource_type_plural, attributes={'subjects': [[grandparent._id, subject._id]]})
        res = app.patch_json_api(url, update_subjects_payload, auth=user_admin_contrib.auth, expect_errors=True)
        assert res.status_code == 400
        assert 'Invalid subject hierarchy' in res.json['errors'][0]['detail']

        # test_unordered_hierarchy
        update_subjects_payload = make_resource_payload(resource, resource_type_plural, attributes={'subjects': [[parent._id, grandparent._id, subject._id]]})
        res = app.patch_json_api(url, update_subjects_payload, auth=user_admin_contrib.auth, expect_errors=True)
        assert res.status_code == 200
        subjects = resource.subjects.all()
        assert parent in subjects
        assert grandparent in subjects
        assert subject in subjects

    def test_set_subjects_as_relationships_validation(self, app, user_admin_contrib, resource, subject, resource_type_plural,
            url, make_resource_payload):

        grandparent = SubjectFactory()
        parent = SubjectFactory(parent=grandparent)
        subject.parent = parent
        subject.save()

        url = '{}?version=2.15'.format(url)
        update_subjects_payload = make_resource_payload(resource, resource_type_plural, relationships={
            'subjects': {
                'data': [
                    {'id': 'bad_id', 'type': 'subjects'}
                ]
            }
        })

        # test_invalid_subject
        res = app.patch_json_api(url, update_subjects_payload, auth=user_admin_contrib.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Subject not found.'

        # test_attribute_payload_instead_of_relationships_payload
        update_subjects_payload = make_resource_payload(resource, resource_type_plural, attributes={'subjects': [[grandparent._id]]})
        res = app.patch_json_api(url, update_subjects_payload, auth=user_admin_contrib.auth, expect_errors=True)
        assert res.status_code == 400
        assert res.json['errors'][0]['detail'] == 'Subjects are improperly formatted. Expecting a list of subjects.'

    def test_set_subjects_as_relationships_hierarchies(self, app, user_admin_contrib, resource, subject, resource_type_plural,
            url, make_resource_payload):

        grandparent = SubjectFactory()
        parent = SubjectFactory(parent=grandparent)
        subject.parent = parent
        subject.save()

        # Sent in level three only
        url = '{}?version=2.15'.format(url)
        update_subjects_payload = make_resource_payload(resource, resource_type_plural, relationships={
            'subjects': {
                'data': [
                    {'id': subject._id, 'type': 'subjects'},
                ]
            }
        })

        res = app.patch_json_api(url, update_subjects_payload, auth=user_admin_contrib.auth, expect_errors=True)
        assert res.status_code == 200
        subjects = resource.subjects.all()
        assert len(subjects) == 3
        assert grandparent in subjects
        assert parent in subjects
        assert subject in subjects

        # Sent in level two only
        update_subjects_payload = make_resource_payload(resource, resource_type_plural, relationships={
            'subjects': {
                'data': [
                    {'id': parent._id, 'type': 'subjects'},
                ]
            }
        })

        res = app.patch_json_api(url, update_subjects_payload, auth=user_admin_contrib.auth, expect_errors=True)
        assert res.status_code == 200
        subjects = resource.subjects.all()
        assert len(subjects) == 2
        assert parent in subjects
        assert grandparent in subjects

        # Sent in two items in hierarchy
        update_subjects_payload = make_resource_payload(resource, resource_type_plural, relationships={
            'subjects': {
                'data': [
                    {'id': parent._id, 'type': 'subjects'},
                    {'id': grandparent._id, 'type': 'subjects'}
                ]
            }
        })

        res = app.patch_json_api(url, update_subjects_payload, auth=user_admin_contrib.auth, expect_errors=True)
        assert res.status_code == 200
        subjects = resource.subjects.all()
        assert len(subjects) == 2
        assert parent in subjects
        assert grandparent in subjects
