import logging

from framework.celery_tasks.handlers import enqueue_task

from osf import models

from website import settings
from website.search.drivers import base
from website.search import elastic_search

logger = logging.getLogger(__name__)


class LegacyElasticsearchDriver(base.SearchDriver):

    def __init__(self, default_index=None):
        self._default_index = default_index

    def setup(self, types=None):
        self.create_index(self._default_index)

    def teardown(self, types=None):
        self.delete_index(self._default_index)

    def search(self, query, index=None, doc_type=None, raw=None, refresh=False):
        return elastic_search.search(
            query,
            index=index or self._default_index,
            doc_type=doc_type,
            raw=raw,
        )

    def search_contributor(self, query, page=0, size=10, exclude=None, current_user=None):
        return elastic_search.search_contributor(
            current_user=current_user,
            exclude=exclude or [],
            index=self._default_index,
            page=page,
            query=query,
            size=size,
        )

    def update_node(self, node, index=None, bulk=False, async=True, saved_fields=None):
        kwargs = {'index': index or self._default_index, 'bulk': bulk}

        if not async:
            return elastic_search.update_node(node, **kwargs)

        node_id = node._id
        # We need the transaction to be committed before trying to run celery tasks.
        # For example, when updating a Node's privacy, is_public must be True in the
        # database in order for method that updates the Node's elastic search document
        # to run correctly.
        if settings.USE_CELERY:
            enqueue_task(elastic_search.update_node_async.s(node_id=node_id, **kwargs))
        else:
            elastic_search.update_node_async(node_id=node_id, **kwargs)

    def update_contributors_async(self, user_id):
        if settings.USE_CELERY:
            enqueue_task(elastic_search.update_contributors_async.s(user_id))
        else:
            elastic_search.update_contributors_async(user_id)

    def update_user(self, user, index=None, async=True):
        index = index or self._default_index
        if not async:
            return elastic_search.update_user(user, index=index)

        user_id = user.id
        if settings.USE_CELERY:
            enqueue_task(elastic_search.update_user_async.s(user_id, index=index))
        else:
            elastic_search.update_user_async(user_id, index=index)

    def update_file(self, file_, index=None, delete=False):
        return elastic_search.update_file(
            file_,
            index=index or self._default_index,
            delete=delete
        )

    def update_institution(self, institution, index=None):
        return elastic_search.update_institution(institution, index=index or self._default_index)

    def update_collected_metadata(self, cgm_id, collection_id=None, index=None, op='update'):
        index = index or self._default_index

        if settings.USE_CELERY:
            enqueue_task(elastic_search.update_cgm_async.s(cgm_id, collection_id=collection_id, op=op, index=index))
        else:
            elastic_search.update_cgm_async(cgm_id, collection_id=collection_id, op=op, index=index)

    def bulk_update_collected_metadata(self, cgms, op='update', index=None):
        index = index or self._default_index
        elastic_search.bulk_update_cgm(cgms, op=op, index=index)

    def bulk_update_nodes(self, serialize, nodes, index=None):
        return elastic_search.bulk_update_nodes(serialize, nodes, index=index or self._default_index)

    def delete_node(self, node, index=None):
        index = index or settings.ELASTIC_INDEX
        doc_type = node.project_or_component
        if node.is_registration:
            doc_type = 'registration'
        elif node.is_preprint:
            doc_type = 'preprint'
        return elastic_search.delete_doc(node._id, node, index=index or self._default_index, category=doc_type)

    def delete_all(self):
        return elastic_search.delete_all()

    def delete_index(self, index):
        return elastic_search.delete_index(index)

    def create_index(self, index=None):
        elastic_search.create_index(index=index or self._default_index)

    # Not implemented on purpose. No need to continue use of this driver

    def index_files(self, **query):
        raise NotImplementedError()

    def index_users(self, **query):
        raise NotImplementedError()

    def index_registrations(self, **query):
        raise NotImplementedError()

    def index_projects(self, **query):
        raise NotImplementedError()

    def index_components(self, **query):
        raise NotImplementedError()

    def index_preprints(self, **query):
        raise NotImplementedError()

    def index_collection_submissions(self, **query):
        for cgm in models.CollectedGuidMetadata.objects.filter(**query).select_related('guid'):
            elastic_search.update_cgm_async(
                cgm.guid._id,
                collection_id=cgm.collection_id,
                index=self._default_index,
            )

    def remove(self, model):
        elastic_search.client().delete(
            doc_type='collectionSubmission',
            id=model._id,
            refresh=True,
            ignore=[404],
            index=self._default_index,
        )
