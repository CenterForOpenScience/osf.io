from __future__ import absolute_import

from django.conf.urls import url

from admin.common_auth import views

app_name = 'admin'

urlpatterns = [
    url(r'^login/?$', views.LoginView.as_view(), name='login'),
    url(r'^logout/$', views.logout_user, name='logout'),
    url(r'^register/$', views.RegisterUser.as_view(), name='register'),
    url(r'^settings/desk/$', views.DeskUserCreateFormView.as_view(), name='desk'),
    url(r'^settings/desk/update/$', views.DeskUserUpdateFormView.as_view(), name='desk_update'),
]
