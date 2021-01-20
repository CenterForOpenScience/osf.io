from django.conf.urls import include, url
from django.views.generic.base import RedirectView


from api.base import views
from api.base import settings
from api.base import versioning

default_version = versioning.decimal_version_to_url_path(settings.REST_FRAMEWORK['DEFAULT_VERSION'])

# Please keep URLs alphabetized for auto-generated documentation

urlpatterns = [
    url(
        r'^_/',
        include(
            [
                url(r'^', include('waffle.urls')),
                url(r'^wb/', include('api.wb.urls', namespace='wb')),
                url(r'^banners/', include('api.banners.urls', namespace='banners')),
                url(r'^crossref/', include('api.crossref.urls', namespace='crossref')),
                url(r'^chronos/', include('api.chronos.urls', namespace='chronos')),
                url(r'^meetings/', include('api.meetings.urls', namespace='meetings')),
                url(r'^metrics/', include('api.metrics.urls', namespace='metrics')),
            ],
        ),
    ),
    url(
        '^(?P<version>(v2))/',
        include(
            [
                url(r'^$', views.root, name='root'),
                url(r'^status/', views.status_check, name='status_check'),
                url(r'^actions/', include('api.actions.urls', namespace='actions')),
                url(r'^addons/', include('api.addons.urls', namespace='addons')),
                url(r'^alerts/', include(('api.alerts.urls', 'alerts'), namespace='alerts')),
                url(r'^applications/', include('api.applications.urls', namespace='applications')),
                url(r'^brands/', include('api.brands.urls', namespace='brands')),
                url(r'^citations/', include('api.citations.urls', namespace='citations')),
                url(r'^collections/', include('api.collections.urls', namespace='collections')),
                url(r'^comments/', include('api.comments.urls', namespace='comments')),
                url(r'^docs/', RedirectView.as_view(pattern_name=views.root), name='redirect-to-root', kwargs={'version': default_version}),
                url(r'^draft_nodes/', include('api.draft_nodes.urls', namespace='draft_nodes')),
                url(r'^draft_registrations/', include('api.draft_registrations.urls', namespace='draft_registrations')),
                url(r'^files/', include('api.files.urls', namespace='files')),
                url(r'^groups/', include('api.osf_groups.urls', namespace='groups')),
                url(r'^guids/', include('api.guids.urls', namespace='guids')),
                url(r'^identifiers/', include('api.identifiers.urls', namespace='identifiers')),
                url(r'^institutions/', include('api.institutions.urls', namespace='institutions')),
                url(r'^licenses/', include('api.licenses.urls', namespace='licenses')),
                url(r'^logs/', include('api.logs.urls', namespace='logs')),
                url(r'^metaschemas/', include('api.metaschemas.urls', namespace='metaschemas')),
                url(r'^schemas/', include('api.schemas.urls', namespace='schemas')),
                url(r'^nodes/', include('api.nodes.urls', namespace='nodes')),
                url(r'^preprints/', include('api.preprints.urls', namespace='preprints')),
                url(r'^preprint_providers/', include('api.preprint_providers.urls', namespace='preprint_providers')),
                url(r'^regions/', include('api.regions.urls', namespace='regions')),
                url(r'^providers/', include('api.providers.urls', namespace='providers')),
                url(r'^registrations/', include('api.registrations.urls', namespace='registrations')),
                url(r'^requests/', include(('api.requests.urls', 'requests'), namespace='requests')),
                url(r'^scopes/', include('api.scopes.urls', namespace='scopes')),
                url(r'^search/', include('api.search.urls', namespace='search')),
                url(r'^sparse/', include('api.sparse.urls', namespace='sparse')),
                url(r'^subjects/', include('api.subjects.urls', namespace='subjects')),
                url(r'^subscriptions/', include('api.subscriptions.urls', namespace='subscriptions')),
                url(r'^taxonomies/', include('api.taxonomies.urls', namespace='taxonomies')),
                url(r'^test/', include('api.test.urls', namespace='test')),
                url(r'^tokens/', include('api.tokens.urls', namespace='tokens')),
                url(r'^users/', include('api.users.urls', namespace='users')),
                url(r'^view_only_links/', include('api.view_only_links.urls', namespace='view-only-links')),
                url(r'^wikis/', include('api.wikis.urls', namespace='wikis')),
                url(r'^_waffle/', include(('api.waffle.urls', 'waffle'), namespace='waffle')),
            ],
        ),
    ),
    url(r'^$', RedirectView.as_view(pattern_name=views.root), name='redirect-to-root', kwargs={'version': default_version}),
]

# Add django-silk URLs if it's in INSTALLED_APPS
if 'silk' in settings.INSTALLED_APPS:
    urlpatterns += [
        url(r'^silk/', include('silk.urls', namespace='silk')),
    ]

if settings.DEBUG:
    import debug_toolbar

    urlpatterns += [
        url(r'^__debug__/', include(debug_toolbar.urls)),
    ]


handler404 = views.error_404
