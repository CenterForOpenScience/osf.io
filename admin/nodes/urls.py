from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.NodeFormView.as_view(),
        name='node_blank'),
    url(r'^id-(?P<guid>[a-z0-9]+)/$', views.NodeFormView.as_view(),
        name='node'),
]
