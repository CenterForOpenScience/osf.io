import pytest

from osf_tests.factories import (
    ProjectFactory,
    CollectionFactory,
    AuthUserFactory
)
from api.base.settings.defaults import API_BASE


@pytest.mark.django_db
class TestNodeCollectionsList:
    @pytest.fixture()
    def user(self):
        return AuthUserFactory()

    @pytest.fixture()
    def user_two(self):
        return AuthUserFactory()

    @pytest.fixture()
    def public_project(self, user):
        return ProjectFactory(is_public=True, creator=user)

    @pytest.fixture()
    def private_project(self, user):
        return ProjectFactory(is_public=False, creator=user)

    @pytest.fixture()
    def collection(self, user):
        return CollectionFactory(creator=user)

    def test_public_node_collections_list_logged_out(self, app, public_project, collection):
        collection.collect_object(public_project, collector=collection.creator)
        res = app.get(f'/{API_BASE}nodes/{public_project._id}/collections/')
        assert res.status_code == 200
        assert len(res.json['data']) == 1
        assert res.json['data'][0]['id'] == collection._id

    def test_public_node_collections_list_logged_in(self, app, user_two, public_project, collection):
        collection.collect_object(public_project, collector=collection.creator)
        res = app.get(f'/{API_BASE}nodes/{public_project._id}/collections/', auth=user_two.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == 1
        assert res.json['data'][0]['id'] == collection._id

    def test_private_node_collections_list_admin(self, app, user, private_project, collection):
        collection.collect_object(private_project, collector=user)
        res = app.get(f'/{API_BASE}nodes/{private_project._id}/collections/', auth=user.auth)
        assert res.status_code == 200
        assert len(res.json['data']) == 1
        assert res.json['data'][0]['id'] == collection._id

    def test_private_node_collections_list_non_contrib(self, app, user_two, private_project, collection):
        collection.collect_object(private_project, collector=collection.creator)
        res = app.get(
            f'/{API_BASE}nodes/{private_project._id}/collections/',
            auth=user_two.auth,
            expect_errors=True
        )
        assert res.status_code == 403

    def test_private_node_collections_list_logged_out(self, app, private_project, collection):
        collection.collect_object(private_project, collector=collection.creator)
        res = app.get(f'/{API_BASE}nodes/{private_project._id}/collections/', expect_errors=True)
        assert res.status_code == 401

    def test_multiple_collections_linked_to_node(self, app, public_project, user):
        collection1 = CollectionFactory(creator=user)
        collection2 = CollectionFactory(creator=user)
        collection3 = CollectionFactory(creator=user)

        collection1.collect_object(public_project, collector=user)
        collection2.collect_object(public_project, collector=user)
        collection3.collect_object(public_project, collector=user)

        res = app.get(f'/{API_BASE}nodes/{public_project._id}/collections/')
        assert res.status_code == 200
        ids = [col['id'] for col in res.json['data']]
        assert set(ids) == {collection1._id, collection2._id, collection3._id}

    def test_remove_node_from_collection(self, app, public_project, user):
        collection1 = CollectionFactory(creator=user)
        collection2 = CollectionFactory(creator=user)

        collection1.collect_object(public_project, collector=user)
        collection2.collect_object(public_project, collector=user)

        # Remove public_project from collection2
        collection2.collectionsubmission_set.first().delete()

        res = app.get(f'/{API_BASE}nodes/{public_project._id}/collections/')
        assert res.status_code == 200
        ids = [col['id'] for col in res.json['data']]
        assert set(ids) == {collection1._id}

    def test_unlinked_collections_not_included(self, app, public_project, user):
        linked = CollectionFactory(creator=user)
        unlinked = CollectionFactory(creator=user)

        linked.collect_object(public_project, collector=user)

        res = app.get(f'/{API_BASE}nodes/{public_project._id}/collections/')
        assert res.status_code == 200
        ids = [col['id'] for col in res.json['data']]
        assert linked._id in ids
        assert unlinked._id not in ids
