from django.conf import settings as drf_settings
from django.conf.urls import include, url
from django.conf.urls.static import static
from django.views.generic.base import RedirectView

from . import views
from . import settings
from . import versioning

default_version = versioning.decimal_version_to_url_path(settings.REST_FRAMEWORK['DEFAULT_VERSION'])

# Please keep URLs alphabetized for auto-generated documentation
urlpatterns = [
    url('^(?P<version>(v2))/',
        include(
            [
                url(r'^$', views.root, name='root'),
                url(r'^status/', views.status_check, name='status_check'),
                url(r'^actions/', include(('api.actions.urls', 'actions'), namespace='actions')),
                url(r'^addons/', include(('api.addons.urls', 'addons'), namespace='addons')),
                url(r'^applications/', include(('api.applications.urls', 'applications'), namespace='applications')),
                url(r'^citations/', include(('api.citations.urls', 'citations'), namespace='citations')),
                url(r'^collections/', include(('api.collections.urls', 'collections'), namespace='collections')),
                url(r'^comments/', include(('api.comments.urls', 'comments'), namespace='comments')),
                url(r'^docs/', RedirectView.as_view(pattern_name=views.root), name='redirect-to-root', kwargs={'version': default_version}),
                url(r'^files/', include(('api.files.urls', 'files'), namespace='files')),
                url(r'^guids/', include(('api.guids.urls', 'guids'), namespace='guids')),
                url(r'^identifiers/', include(('api.identifiers.urls', 'identifiers'), namespace='identifiers')),
                url(r'^institutions/', include(('api.institutions.urls', 'institutions'), namespace='institutions')),
                url(r'^licenses/', include(('api.licenses.urls', 'licenses'), namespace='licenses')),
                url(r'^logs/', include(('api.logs.urls', 'logs'), namespace='logs')),
                url(r'^metaschemas/', include(('api.metaschemas.urls', 'metaschemas'), namespace='metaschemas')),
                url(r'^nodes/', include(('api.nodes.urls', 'nodes'), namespace='nodes')),
                url(r'^preprints/', include(('api.preprints.urls', 'preprints'), namespace='preprints')),
                url(r'^preprint_providers/', include(('api.preprint_providers.urls', 'preprint_providers'), namespace='preprint_providers')),
                url(r'^registrations/', include(('api.registrations.urls', 'registrations'), namespace='registrations')),
                url(r'^search/', include(('api.search.urls', 'search'), namespace='search')),
                url(r'^taxonomies/', include(('api.taxonomies.urls', 'taxonomies'), namespace='taxonomies')),
                url(r'^test/', include(('api.test.urls', 'test'), namespace='test')),
                url(r'^tokens/', include(('api.tokens.urls', 'tokens'), namespace='tokens')),
                url(r'^users/', include(('api.users.urls', 'users'), namespace='users')),
                url(r'^view_only_links/', include(('api.view_only_links.urls', 'view_only_links'), namespace='view-only-links')),
                url(r'^wikis/', include(('api.wikis.urls', 'wikis'), namespace='wikis')),
            ],
        )
        ),
    url(r'^$', RedirectView.as_view(pattern_name=views.root), name='redirect-to-root', kwargs={'version': default_version})
]


urlpatterns += static('/static/', document_root=drf_settings.STATIC_ROOT)

handler404 = views.error_404
