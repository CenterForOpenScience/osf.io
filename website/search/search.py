import logging

from framework.celery_tasks.handlers import enqueue_task

from website import settings

logger = logging.getLogger(__name__)

if settings.SEARCH_ENGINE == 'elastic':
    import website.search.elastic_search as search_engine
else:
    search_engine = None
    logger.warn('Elastic search is not set to load')

def requires_search(func):
    def wrapped(*args, **kwargs):
        if search_engine is not None and not settings.RUNNING_MIGRATION:
            return func(*args, **kwargs)
    return wrapped


@requires_search
def search(query, index=None, doc_type=None, raw=None):
    index = index or settings.ELASTIC_INDEX
    return search_engine.search(query, index=index, doc_type=doc_type, raw=raw)

@requires_search
def update_node(node, index=None, bulk=False, async_update=True, saved_fields=None):
    kwargs = {
        'index': index,
        'bulk': bulk
    }
    if async_update:
        node_id = node._id
        # We need the transaction to be committed before trying to run celery tasks.
        # For example, when updating a Node's privacy, is_public must be True in the
        # database in order for method that updates the Node's elastic search document
        # to run correctly.
        if settings.USE_CELERY:
            enqueue_task(search_engine.update_node_async.s(node_id=node_id, **kwargs))
        else:
            search_engine.update_node_async(node_id=node_id, **kwargs)
    else:
        index = index or settings.ELASTIC_INDEX
        return search_engine.update_node(node, **kwargs)

@requires_search
def update_preprint(preprint, index=None, bulk=False, async_update=True, saved_fields=None):
    kwargs = {
        'index': index,
        'bulk': bulk
    }
    if async_update:
        preprint_id = preprint._id
        # We need the transaction to be committed before trying to run celery tasks.
        if settings.USE_CELERY:
            enqueue_task(search_engine.update_preprint_async.s(preprint_id=preprint_id, **kwargs))
        else:
            search_engine.update_preprint_async(preprint_id=preprint_id, **kwargs)
    else:
        index = index or settings.ELASTIC_INDEX
        return search_engine.update_preprint(preprint, **kwargs)

@requires_search
def bulk_update_nodes(serialize, nodes, index=None, category=None):
    index = index or settings.ELASTIC_INDEX
    search_engine.bulk_update_nodes(serialize, nodes, index=index, category=category)

@requires_search
def delete_node(node, index=None):
    index = index or settings.ELASTIC_INDEX
    doc_type = node.project_or_component
    if node.is_registration:
        doc_type = 'registration'
    search_engine.delete_doc(node._id, node, index=index, category=doc_type)

@requires_search
def update_contributors_async(user_id):
    """Async version of update_contributors above"""
    if settings.USE_CELERY:
        enqueue_task(search_engine.update_contributors_async.s(user_id))
    else:
        search_engine.update_contributors_async(user_id)

@requires_search
def update_user(user, index=None, async_update=True):
    index = index or settings.ELASTIC_INDEX
    if async_update:
        user_id = user.id
        if settings.USE_CELERY:
            enqueue_task(search_engine.update_user_async.s(user_id, index=index))
        else:
            search_engine.update_user_async(user_id, index=index)
    else:
        search_engine.update_user(user, index=index)

@requires_search
def update_file(file_, index=None, delete=False):
    index = index or settings.ELASTIC_INDEX
    search_engine.update_file(file_, index=index, delete=delete)

@requires_search
def update_institution(institution, index=None):
    index = index or settings.ELASTIC_INDEX
    search_engine.update_institution(institution, index=index)

@requires_search
def update_collected_metadata(cgm_id, collection_id=None, index=None, op='update'):
    index = index or settings.ELASTIC_INDEX

    if settings.USE_CELERY:
        enqueue_task(search_engine.update_cgm_async.s(cgm_id, collection_id=collection_id, op=op, index=index))
    else:
        search_engine.update_cgm_async(cgm_id, collection_id=collection_id, op=op, index=index)

@requires_search
def bulk_update_collected_metadata(cgms, op='update', index=None):
    index = index or settings.ELASTIC_INDEX
    search_engine.bulk_update_cgm(cgms, op=op, index=index)

@requires_search
def delete_all():
    search_engine.delete_all()

@requires_search
def delete_index(index):
    search_engine.delete_index(index)

@requires_search
def create_index(index=None):
    index = index or settings.ELASTIC_INDEX
    search_engine.create_index(index=index)


@requires_search
def search_contributor(query, page=0, size=10, exclude=None, current_user=None):
    exclude = exclude or []
    result = search_engine.search_contributor(query=query, page=page, size=size,
                                              exclude=exclude, current_user=current_user)
    return result
