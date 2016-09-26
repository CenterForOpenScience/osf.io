from django.conf import settings
from django.conf.urls import include, url
from django.conf.urls.static import static
from django.views.generic.base import RedirectView
from settings import API_BASE

from . import views

base_pattern = '^{}'.format(API_BASE)

# Please keep URLs alphabetized for auto-generated documentation

urlpatterns = [
    url(base_pattern,
        include(
            [
                url(r'^$', views.root, name='root'),
                url(r'^addons/', include('api.addons.urls', namespace='addons')),
                url(r'^applications/', include('api.applications.urls', namespace='applications')),
                url(r'^citations/', include('api.citations.urls', namespace='citations')),
                url(r'^collections/', include('api.collections.urls', namespace='collections')),
                url(r'^comments/', include('api.comments.urls', namespace='comments')),
                url(r'^docs/', include('rest_framework_swagger.urls')),
                url(r'^files/', include('api.files.urls', namespace='files')),
                url(r'^guids/', include('api.guids.urls', namespace='guids')),
                url(r'^identifiers/', include('api.identifiers.urls', namespace='identifiers')),
                url(r'^institutions/', include('api.institutions.urls', namespace='institutions')),
                url(r'^licenses/', include('api.licenses.urls', namespace='licenses')),
                url(r'^logs/', include('api.logs.urls', namespace='logs')),
                url(r'^metaschemas/', include('api.metaschemas.urls', namespace='metaschemas')),
                url(r'^nodes/', include('api.nodes.urls', namespace='nodes')),
                url(r'^preprints/', include('api.preprints.urls', namespace='preprints')),
                url(r'^preprint_providers/', include('api.preprint_providers.urls', namespace='preprint_providers')),
                url(r'^registrations/', include('api.registrations.urls', namespace='registrations')),
                url(r'^search/', include('api.search.urls', namespace='search')),
                url(r'^taxonomies/', include('api.taxonomies.urls', namespace='taxonomies')),
                url(r'^test/', include('api.test.urls', namespace='test')),
                url(r'^tokens/', include('api.tokens.urls', namespace='tokens')),
                url(r'^users/', include('api.users.urls', namespace='users')),
                url(r'^view_only_links/', include('api.view_only_links.urls', namespace='view-only-links')),
                url(r'^wikis/', include('api.wikis.urls', namespace='wikis')),
            ],
        )
        ),
    url(r'^$', RedirectView.as_view(pattern_name=views.root), name='redirect-to-root')
]


urlpatterns += static('/static/', document_root=settings.STATIC_ROOT)

handler404 = views.error_404
