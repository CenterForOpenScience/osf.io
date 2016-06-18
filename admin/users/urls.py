from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.UserFormView.as_view(),
        name='search'),
    url(r'^(?P<guid>[a-z0-9]+)/$', views.UserView.as_view(),
        name='user'),
    url(r'^(?P<guid>[a-z0-9]+)/reset-password/$',
        views.ResetPasswordView.as_view(),
        name='reset_password'),
    url(r'^(?P<guid>[a-z0-9]+)/disable/$', views.UserDeleteView.as_view(),
        name='disable'),
    url(r'^(?P<guid>[a-z0-9]+)/reactivate/$', views.UserDeleteView.as_view(),
        name='reactivate'),
    url(r'^(?P<guid>[a-z0-9]+)/two-factor/disable/$',
        views.User2FactorDeleteView.as_view(),
        name='remove2factor'),
]
