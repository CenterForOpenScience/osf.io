from django.conf.urls import include, url
from django.contrib import admin

from settings import ADMIN_BASE

from . import views

base_pattern = '^{}'.format(ADMIN_BASE)

urlpatterns = [
    ### ADMIN ###
    url(
        base_pattern,
        include([
            url(r'^$', views.home, name='home'),
            url(r'^admin/', admin.site.urls),
            url(r'^spam/', include('admin.spam.urls', namespace='spam')),
            url(r'^institutions/', include('admin.institutions.urls', namespace='institutions')),
            url(r'^preprint_providers/', include('admin.preprint_providers.urls', namespace='preprint_providers')),
            url(r'^account/', include('admin.common_auth.urls', namespace='auth')),
            url(r'^password/', include('password_reset.urls')),
            url(r'^nodes/', include('admin.nodes.urls', namespace='nodes')),
            url(r'^preprints/', include('admin.preprints.urls', namespace='preprints')),
            url(r'^subjects/', include('admin.subjects.urls', namespace='subjects')),
            url(r'^users/', include('admin.users.urls', namespace='users')),
            url(r'^meetings/', include('admin.meetings.urls',
                                       namespace='meetings')),
            url(r'^project/', include('admin.pre_reg.urls', namespace='pre_reg')),
            url(r'^metrics/', include('admin.metrics.urls',
                                      namespace='metrics')),
            url(r'^desk/', include('admin.desk.urls',
                                   namespace='desk')),
        ]),
    ),
]

admin.site.site_header = 'OSF-Admin administration'
