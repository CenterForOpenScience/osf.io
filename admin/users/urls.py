from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.UserFormView.as_view(),
        name='user_blank'),
    url(r'^id-(?P<guid>[a-z0-9]+)/$', views.UserFormView.as_view(),
        name='user'),
]
