from django.conf.urls import include, url
from django.contrib import admin
from admin.base.settings import ADMIN_BASE, DEBUG
from admin.base import views

base_pattern = '^{}'.format(ADMIN_BASE)

urlpatterns = [
    ### ADMIN ###
    url(
        base_pattern,
        include([
            url(r'^$', views.home, name='home'),
            url(r'^admin/', admin.site.urls),
            url(r'^asset_files/', include('admin.asset_files.urls', namespace='asset_files')),
            url(r'^banners/', include('admin.banners.urls', namespace='banners')),
            url(r'^spam/', include('admin.spam.urls', namespace='spam')),
            url(r'^institutions/', include('admin.institutions.urls', namespace='institutions')),
            url(r'^preprint_providers/', include('admin.preprint_providers.urls', namespace='preprint_providers')),
            url(r'^collection_providers/', include('admin.collection_providers.urls', namespace='collection_providers')),
            url(r'^registration_providers/', include('admin.registration_providers.urls', namespace='registration_providers')),
            url(r'^account/', include('admin.common_auth.urls', namespace='auth')),
            url(r'^password/', include('password_reset.urls')),
            url(r'^nodes/', include('admin.nodes.urls', namespace='nodes')),
            url(r'^preprints/', include('admin.preprints.urls', namespace='preprints')),
            url(r'^subjects/', include('admin.subjects.urls', namespace='subjects')),
            url(r'^users/', include('admin.users.urls', namespace='users')),
            url(r'^maintenance/', include('admin.maintenance.urls', namespace='maintenance')),
            url(r'^meetings/', include('admin.meetings.urls',
                                       namespace='meetings')),
            url(r'^project/', include('admin.pre_reg.urls', namespace='pre_reg')),
            url(r'^metrics/', include('admin.metrics.urls',
                                      namespace='metrics')),
            url(r'^desk/', include('admin.desk.urls',
                                   namespace='desk')),
            url(r'^osf_groups/', include('admin.osf_groups.urls', namespace='osf_groups')),
        ]),
    ),
]

if DEBUG:
    import debug_toolbar

    urlpatterns += [
        url(r'^__debug__/', include(debug_toolbar.urls)),
    ]

admin.site.site_header = 'OSF-Admin administration'
