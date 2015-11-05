from django.conf.urls import include, url, patterns
from settings import ADMIN_BASE

from . import views

base_pattern = '^{}'.format(ADMIN_BASE)

urlpatterns = [
    ### ADMIN ###
    url(base_pattern,
        include(patterns('',
                         url(r'^$', views.root),
                         url(r'^spam/', include('admin.spam.urls', namespace='spam')),
                         url(r'^auth/', include('admin.common_auth.urls', namespace='common_auth')),
                         )
                )
        )
]
