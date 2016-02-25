from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.NodeFormView.as_view(),
        name='search'),
    url(r'^id-(?P<guid>[a-z0-9]+)/$', views.NodeView.as_view(),
        name='node'),
    url(r'^registration_list/$', views.RegistrationListView.as_view(),
        name='registrations'),
]
