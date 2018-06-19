from werkzeug.local import LocalProxy

from website import settings


__all__ = ('search', 'driver', '_driver')

if settings.SEARCH_ENGINE is None:
    from website.search.drivers.disabled import SearchDisabledDriver
    _driver = SearchDisabledDriver()
elif settings.SEARCH_ENGINE in ('elastic', 'legacy_elasticsearch'):
    from website.search.drivers.legacy_elasticsearch import LegacyElasticsearchDriver
    _driver = LegacyElasticsearchDriver(settings.ELASTIC_INDEX)
else:
    raise RuntimeError('Unknown Search Engine "{}"'.format(settings.SEARCH_ENGINE))

def _get_driver():
    return _driver

search = driver = LocalProxy(_get_driver)
