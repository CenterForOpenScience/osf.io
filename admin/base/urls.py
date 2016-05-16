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
            url(r'^admin/', include(admin.site.urls)),
            url(r'^spam/', include('admin.spam.urls', namespace='spam')),
            url(r'^account/', include('admin.common_auth.urls', namespace='auth')),
            url(r'^password/', include('password_reset.urls')),
            url(r'^nodes/', include('admin.nodes.urls', namespace='nodes')),
            url(r'^users/', include('admin.users.urls', namespace='users')),
            url(r'^project/', include('admin.pre_reg.urls', namespace='pre_reg')),
            url(r'^metrics/', include('admin.metrics.urls',
                                      namespace='metrics')),
            url(r'^desk/', include('admin.desk.urls',
                                   namespace='desk')),
        ]),
    ),
]

admin.site.site_header = 'OSF-Admin administration'
