from __future__ import absolute_import

from django.conf.urls import url
from django.core.urlresolvers import reverse_lazy
from django.contrib.auth.views import password_change, password_change_done

from admin.common_auth import views

urlpatterns = [
    url(r'^login/?$', views.LoginView.as_view(), name='login'),
    url(r'^logout/$', views.logout_user, name='logout'),
    url(r'^register/$', views.RegisterUser.as_view(), name='register'),
    url(r'^password_change/$', password_change,
        {'post_change_redirect': reverse_lazy('auth:password_change_done')},
        name='password_change'),
    url(r'^password_change/done/$', password_change_done,
        {'template_name': 'password_change_done.html'},
        name='password_change_done'),
    url(r'^settings/desk/$', views.DeskUserFormView.as_view(), name='desk'),
]
