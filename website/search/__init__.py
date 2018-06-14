from website import settings

__all__ = ('search', )

if settings.SEARCH_ENGINE is None:
    from website.search.drivers.disabled import SearchDisabledDriver
    search = SearchDisabledDriver()
elif settings.SEARCH_ENGINE in ('elastic', 'legacy_elasticsearch'):
    from website.search.drivers.legacy_elasticsearch import LegacyElasticsearchDriver
    search = LegacyElasticsearchDriver(settings.ELASTIC_INDEX)
else:
    raise RuntimeError('Unknown Search Engine "{}"'.format(settings.SEARCH_ENGINE))
