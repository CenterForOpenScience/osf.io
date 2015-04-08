import urlparse
from modularodm.exceptions import NoResultsFound
from modularodm import Q
from rest_framework.exceptions import NotFound
from rest_framework.reverse import reverse

from website import settings


def absolute_reverse(*args, **kwargs):
    """Like django's `reverse`, except returns an absolute URL."""
    relative_url = reverse(*args, **kwargs)
    return urlparse.urljoin(settings.DOMAIN, relative_url)


def get_object_or_404(model_cls, query_or_pk):
    if isinstance(query_or_pk, basestring):
        query = Q('_id', 'eq', query_or_pk)
    else:
        query = query_or_pk
    try:
        return model_cls.find_one(query)
    except NoResultsFound:
        raise NotFound
