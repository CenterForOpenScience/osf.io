from django.conf.urls import include, url, patterns
from settings import ADMIN_BASE

from . import views

base_pattern = '^{}'.format(ADMIN_BASE)

urlpatterns = [
    ### ADMIN ###
    url(base_pattern,
        include(patterns('',
                         url(r'^$', views.root, name='home'),
                         url(r'^spam/', include('admin.spam.urls', namespace='spam')),
                         url(r'^pre-reg/', include('admin.pre-reg.urls', namespace='pre-reg')),
                         )
                )
        )
]
