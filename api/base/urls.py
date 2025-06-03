from django.urls import include, re_path
from django.views.generic.base import RedirectView


from api.base import views
from api.base import settings
from api.base import versioning
from api.providers.views import RegistrationBulkCreate

default_version = versioning.decimal_version_to_url_path(settings.REST_FRAMEWORK['DEFAULT_VERSION'])

# Please keep URLs alphabetized for auto-generated documentation

urlpatterns = [
    re_path(
        r'^_/',
        include(
            [
                re_path(r'^', include('waffle.urls')),
                re_path(r'^wb/', include('api.wb.urls', namespace='wb')),
                re_path(r'^ia/', include('api.ia.urls', namespace='ia')),
                re_path(r'^banners/', include('api.banners.urls', namespace='banners')),
                re_path(r'^crossref/', include('api.crossref.urls', namespace='crossref')),
                re_path(r'^chronos/', include('api.chronos.urls', namespace='chronos')),
                re_path(r'^cedar_metadata_templates/', include('api.cedar_metadata_templates.urls', namespace='cedar-metadata-templates')),
                re_path(r'^cedar_metadata_records/', include('api.cedar_metadata_records.urls', namespace='cedar-metadata-records')),
                re_path(r'^meetings/', include('api.meetings.urls', namespace='meetings')),
                re_path(r'^metrics/', include('api.metrics.urls', namespace='metrics')),
                re_path(r'^registries/(?P<provider_id>\w+)/bulk_create/(?P<filename>.*)/$', RegistrationBulkCreate.as_view(), name='bulk_create_csv'),
            ],
        ),
    ),
    re_path(
        '^(?P<version>(v2))/',
        include(
            [
                re_path(r'^$', views.root, name='root'),
                re_path(r'^status/', views.status_check, name='status_check'),
                re_path(r'^actions/', include('api.actions.urls', namespace='actions')),
                re_path(r'^addons/', include('api.addons.urls', namespace='addons')),
                re_path(r'^alerts/', include(('api.alerts.urls', 'alerts'), namespace='alerts')),
                re_path(r'^applications/', include('api.applications.urls', namespace='applications')),
                re_path(r'^brands/', include('api.brands.urls', namespace='brands')),
                re_path(r'^citations/', include('api.citations.urls', namespace='citations')),
                re_path(r'^collections/', include('api.collections.urls', namespace='collections')),
                re_path(r'^collection_submissions/', include('api.collection_submissions.urls', namespace='collection_submissions')),
                re_path(r'^collection_submission_actions/', include('api.collection_submission_actions.urls', namespace='collection_submission_actions')),
                re_path(r'^collection_subscriptions/', include('api.collection_subscriptions.urls', namespace='collection_subscriptions')),
                re_path(r'^comments/', include('api.comments.urls', namespace='comments')),
                re_path(r'^custom_file_metadata_records/', include('api.custom_metadata.file_urls', namespace='custom-file-metadata')),
                re_path(r'^custom_item_metadata_records/', include('api.custom_metadata.item_urls', namespace='custom-item-metadata')),
                re_path(r'^docs/', RedirectView.as_view(pattern_name=views.root), name='redirect-to-root', kwargs={'version': default_version}),
                re_path(r'^draft_nodes/', include('api.draft_nodes.urls', namespace='draft_nodes')),
                re_path(r'^draft_registrations/', include('api.draft_registrations.urls', namespace='draft_registrations')),
                re_path(r'^files/', include('api.files.urls', namespace='files')),
                re_path(r'^guids/', include('api.guids.urls', namespace='guids')),
                re_path(r'^identifiers/', include('api.identifiers.urls', namespace='identifiers')),
                re_path(r'^institutions/', include('api.institutions.urls', namespace='institutions')),
                re_path(r'^licenses/', include('api.licenses.urls', namespace='licenses')),
                re_path(r'^logs/', include('api.logs.urls', namespace='logs')),
                re_path(r'^metaschemas/', include('api.metaschemas.urls', namespace='metaschemas')),
                re_path(r'^schemas/', include('api.schemas.urls', namespace='schemas')),
                re_path(r'^nodes/', include('api.nodes.urls', namespace='nodes')),
                re_path(r'^preprints/', include('api.preprints.urls', namespace='preprints')),
                re_path(r'^preprint_providers/', include('api.preprint_providers.urls', namespace='preprint_providers')),
                re_path(r'^providers/', include('api.providers.urls', namespace='providers')),
                re_path(r'^regions/', include('api.regions.urls', namespace='regions')),
                re_path(r'^registrations/', include('api.registrations.urls', namespace='registrations')),
                re_path(r'^registration_subscriptions/', include('api.registration_subscriptions.urls', namespace='registration_subscriptions')),
                re_path(r'^requests/', include(('api.requests.urls', 'requests'), namespace='requests')),
                re_path(r'^resources/', include('api.resources.urls', namespace='resources')),
                re_path(r'^scopes/', include('api.scopes.urls', namespace='scopes')),
                re_path(r'^search/', include('api.search.urls', namespace='search')),
                re_path(r'^sparse/', include('api.sparse.urls', namespace='sparse')),
                re_path(r'^subjects/', include('api.subjects.urls', namespace='subjects')),
                re_path(r'^subscriptions/', include('api.subscriptions.urls', namespace='subscriptions')),
                re_path(r'^taxonomies/', include('api.taxonomies.urls', namespace='taxonomies')),
                re_path(r'^test/', include('api.test.urls', namespace='test')),
                re_path(r'^tokens/', include('api.tokens.urls', namespace='tokens')),
                re_path(r'^users/', include('api.users.urls', namespace='users')),
                re_path(r'^view_only_links/', include('api.view_only_links.urls', namespace='view-only-links')),
                re_path(r'^wikis/', include('api.wikis.urls', namespace='wikis')),
                re_path(r'^schema_responses/', include('api.schema_responses.urls', namespace='schema_responses')),
                re_path(r'^_waffle/', include(('api.waffle.urls', 'waffle'), namespace='waffle')),
            ],
        ),
    ),
    re_path(r'^$', RedirectView.as_view(pattern_name=views.root), name='redirect-to-root', kwargs={'version': default_version}),
]

# Add django-silk URLs if it's in INSTALLED_APPS
if 'silk' in settings.INSTALLED_APPS:
    urlpatterns += [
        re_path(r'^silk/', include('silk.urls', namespace='silk')),
    ]

if settings.DEBUG:
    import debug_toolbar

    urlpatterns += [
        re_path(r'^__debug__/', include(debug_toolbar.urls)),
    ]


handler404 = views.error_404
