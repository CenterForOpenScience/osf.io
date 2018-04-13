import pytest

from api.base.settings.defaults import API_BASE
from osf_tests.factories import (
    CollectionFactory,
    ProjectFactory,
    AuthUserFactory,
    SubjectFactory,
    CollectionProviderFactory,
)

@pytest.fixture()
def user_one():
    return AuthUserFactory()

@pytest.mark.django_db
class TestCollectedMetaList:
    @pytest.fixture()
    def collection_provider(self, primary_collection):
        cp = CollectionProviderFactory()
        cp.allow_submissions = False
        cp.primary_collection = primary_collection
        cp.save()
        return cp

    @pytest.fixture()
    def user_two(self):
        return AuthUserFactory()

    @pytest.fixture()
    def project_one(self, user_one):
        return ProjectFactory(creator=user_one)

    @pytest.fixture()
    def project_two(self, user_one):
        return ProjectFactory(creator=user_one)

    @pytest.fixture()
    def subject_one(self):
        return SubjectFactory()

    @pytest.fixture()
    def collection_with_provider(self, user_one, project_one):
        c = CollectionFactory(creator=user_one)
        c.collect_object(project_one, user_one, status='asdf')
        return c

    @pytest.fixture()
    def collection_without_provider(self, user_one, project_one):
        c = CollectionFactory(creator=user_one)
        c.collect_object(project_one, user_one)
        return c

    @pytest.fixture()
    def primary_collection(self, user_one, project_one):
        c = CollectionFactory(creator=user_one)
        c.collect_object(project_one, user_one, status='fdsa')
        return c

    @pytest.fixture()
    def url(self, collection_provider):
        return '/{}providers/collections/{}/submissions/'.format(API_BASE, collection_provider._id)

    @pytest.fixture()
    def payload(self):
        def make_collection_payload(**attributes):
            return {
                'data': {
                    'type': 'collected-metadata',
                    'attributes': attributes,
                }
            }
        return make_collection_payload

    def test_no_permissions(self, app, collection_provider, collection_with_provider, collection_without_provider, user_one, user_two, project_two, url, payload):
        # Private

        # Sanity Check
        assert collection_provider.allow_submissions is False

        res = app.get(url)
        assert res.status_code == 200
        assert len(res.json['data']) == 1

        res = app.get(url, auth=user_two.auth)
        assert res.status_code == 200

        res = app.post_json_api(
            url,
            payload(creator=user_two._id, guid=project_two._id, status='asdf'),
            expect_errors=True)
        assert res.status_code == 401

        res = app.post_json_api(
            url,
            payload(creator=user_two._id, guid=project_two._id, status='asdf'),
            auth=user_two.auth,
            expect_errors=True)
        assert res.status_code == 403

        # Public, accepting submissions
        collection_provider.allow_submissions = True
        collection_provider.save()
        collection_provider.primary_collection.is_public = True
        collection_provider.primary_collection.save()
        res = app.get(url)
        assert len(res.json['data']) == 1
        assert res.status_code == 200

        res = app.get(url, auth=user_two.auth)
        assert len(res.json['data']) == 1
        assert res.status_code == 200

        res = app.post_json_api(
            url,
            payload(creator=user_two._id, guid=project_two._id, status='asdf'),
            expect_errors=True)
        assert res.status_code == 401

        res = app.post_json_api(
            url,
            payload(creator=user_two._id, guid=project_two._id, status='asdf'),
            auth=user_two.auth,
            expect_errors=True)
        # Neither collection perms nor project perms
        assert res.status_code == 403

        project_three = ProjectFactory(creator=user_two)  # has_referent_perm

        res = app.post_json_api(
            url,
            payload(creator=user_two._id, guid=project_three._id, status='asdf'),
            auth=user_two.auth,
            expect_errors=True)
        assert res.status_code == 201

        assert not (collection_with_provider.guid_links.all() | collection_without_provider.guid_links.all()).filter(_id=project_three._id).exists()
        assert collection_provider.primary_collection.guid_links.filter(_id=project_three._id).exists()

    def test_with_permissions(self, app, collection_provider, collection_with_provider, collection_without_provider, user_one, user_two, project_two, subject_one, url, payload):
        res = app.get(url, auth=user_one.auth)
        assert len(res.json['data']) == 1
        assert res.status_code == 200

        res = app.post_json_api(
            url,
            payload(guid=project_two._id, status='asdf', subjects=[[subject_one._id]]),
            auth=user_one.auth)
        assert res.status_code == 201

        project_three = ProjectFactory(creator=user_two)  # user_one does not has_referent_perm

        res = app.post_json_api(
            url,
            payload(guid=project_three._id, status='asdf', subjects=[[subject_one._id]]),
            auth=user_one.auth)
        assert res.status_code == 201

        res = app.get(url, auth=user_one.auth)
        assert len(res.json['data']) == 3
        assert res.status_code == 200

        assert not (collection_with_provider.guid_links.all() | collection_without_provider.guid_links.all()).filter(_id__in=[project_two._id, project_three._id]).exists()
        assert collection_provider.primary_collection.guid_links.filter(_id__in=[project_two._id, project_three._id]).count() == 2

    def test_choice_restrictions(self, app, collection_provider, user_one, project_two, subject_one, url, payload):
        collection_provider.primary_collection.status_choices = ['one', 'two', 'three']
        collection_provider.primary_collection.collected_type_choices = ['asdf', 'fdsa']
        collection_provider.primary_collection.save()

        # Needs collected_type
        res = app.post_json_api(
            url,
            payload(guid=project_two._id, status='one', subjects=[[subject_one._id]]),
            auth=user_one.auth,
            expect_errors=True)
        assert res.status_code == 400
        assert 'not an acceptable "type"' in res.json['errors'][0]['detail']

        # Needs status
        res = app.post_json_api(
            url,
            payload(guid=project_two._id, collected_type='asdf', subjects=[[subject_one._id]]),
            auth=user_one.auth,
            expect_errors=True)
        assert res.status_code == 400
        assert 'not an acceptable "status"' in res.json['errors'][0]['detail']

        # Invalid status
        res = app.post_json_api(
            url,
            payload(guid=project_two._id, collected_type='asdf', status='asdf', subjects=[[subject_one._id]]),
            auth=user_one.auth,
            expect_errors=True)
        assert res.status_code == 400
        assert 'not an acceptable "status"' in res.json['errors'][0]['detail']

        # Invalid collected_type
        res = app.post_json_api(
            url,
            payload(guid=project_two._id, collected_type='one', status='one', subjects=[[subject_one._id]]),
            auth=user_one.auth,
            expect_errors=True)
        assert res.status_code == 400
        assert 'not an acceptable "type"' in res.json['errors'][0]['detail']

        # Valid
        res = app.post_json_api(
            url,
            payload(guid=project_two._id, collected_type='asdf', status='two', subjects=[[subject_one._id]]),
            auth=user_one.auth)
        assert res.status_code == 201

    def test_filters(self, app, collection_provider, collection_with_provider, collection_without_provider, user_one, user_two, project_one, project_two, subject_one, url, payload):
        res = app.get('{}?filter[id]={}'.format(url, project_one._id), auth=user_one.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == 1
        res = app.get('{}?filter[id]={}'.format(url, project_two._id), auth=user_one.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == 0
        res = app.get('{}?filter[status]=fdsa'.format(url), auth=user_one.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == 1
        res = app.get('{}?filter[collected_type]=asdf'.format(url), auth=user_one.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == 0

        # Sanity
        res = app.get('{}?filter[subjects]={}'.format(url, subject_one._id), auth=user_one.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == 0

        # Add one with a subject to filter for it
        res = app.post_json_api(
            url,
            payload(guid=project_two._id, collected_type='asdf', subjects=[[subject_one._id]]),
            auth=user_one.auth)
        assert res.status_code == 201

        res = app.get('{}?filter[subjects]={}'.format(url, subject_one._id), auth=user_one.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == 1
        res = app.get('{}?filter[collected_type]=asdf'.format(url), auth=user_one.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == 1
