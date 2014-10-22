from website import settings
import logging


logger = logging.getLogger(__name__)

if settings.SEARCH_ENGINE == 'elastic':
    import elastic_search as search_engine
else:
    search_engine = None
    logger.warn('Elastic search is not set to load')


def requires_search(func):
    def wrapped(*args, **kwargs):
        if search_engine is not None:
            return func(*args, **kwargs)
    return wrapped


@requires_search
def search(query, index='_all', _type=None):
    return search_engine.search(query, index=index, search_type=_type)

@requires_search
def update_node(node, index='website'):
    search_engine.update_node(node)


@requires_search
def update_user(user):
    search_engine.update_user(user)


@requires_search
def delete_all():
    search_engine.delete_all()


@requires_search
def search_contributor(query, page=0, size=10, exclude=None, current_user=None):
    result = search_engine.search_contributor(query=query, page=page, size=size,
                                              exclude=exclude, current_user=current_user)
    return result


@requires_search
def update_metadata(metadata):
    search_engine.update_metadata(metadata)
