from django.conf.urls import include, url, patterns
from django.contrib import admin
from settings import ADMIN_BASE
admin.autodiscover()

from . import views

base_pattern = '^{}'.format(ADMIN_BASE)

urlpatterns = [
    ### ADMIN ###
    url(base_pattern,
        include(patterns('',
                         url(r'^$', views.root),
                         url(r'^django_admin/', include(admin.site.urls)),
                         url(r'^spam/', include('admin.spam.urls', namespace='spam')),
                         url(r'^auth/', include('admin.common_auth.urls', namespace='auth')),
                         )
                )
        )
]
