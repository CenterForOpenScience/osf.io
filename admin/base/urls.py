from django.conf.urls import include, url
from django.contrib import admin
from django.core.urlresolvers import reverse_lazy
from django.views.generic import RedirectView

from settings import ADMIN_BASE

from . import views

base_pattern = '^{}'.format(ADMIN_BASE)

urlpatterns = [
    ### ADMIN ###
    url(r'^project/', include('admin.pre_reg.urls', namespace='pre_reg')),
    url(base_pattern,
        include([
            url(r'^$', views.home, name='home'),
            url(r'^django_admin/', include(admin.site.urls)),
            url(r'^spam/', include('admin.spam.urls', namespace='spam')),
            url(r'^auth/', include('admin.common_auth.urls', namespace='auth')),
            url(r'^nodes/', include('admin.nodes.urls', namespace='nodes')),
            url(r'^users/', include('admin.users.urls', namespace='users')),
            url(r'^prereg/', include('admin.pre_reg.urls', namespace='pre_reg')),
            url(r'^reset/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$',
                views.password_reset_confirm_custom, name='password_reset_confirm'),
            url(r'^accounts/password_reset/$',
                'django.contrib.auth.views.password_reset',
                name='reset_password'),
            url(
                r'^accounts/password_reset/confirm/(?P<uidb64>[0-9A-Za-z_\-]+)/(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$',
                views.password_reset_confirm_custom,
                name='password_reset_confirm'),
            url(r'^accounts/password_reset/done/$',
                'django.contrib.auth.views.password_reset_done',
                name='password_reset_done'),
            url(r'^accounts/password_reset/complete/$',
                'django.contrib.auth.views.password_reset_complete',
                name='password_reset_complete'),
            url(r'^accounts/password_change/$',
                'django.contrib.auth.views.password_change',
                {'post_change_redirect': reverse_lazy('password_change_done')},
                name="password_change"),
            url(r'^accounts/password_change/done/$',
                'django.contrib.auth.views.password_change_done',
                {'template_name': 'registration/password_change_done.html'},
                name='password_change_done'),
        ])
        ),
    url(r'^$', RedirectView.as_view(url='/admin/')),
]
