from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.PreprintList.as_view(), name=views.PreprintList.view_name),
    url(r'^(?P<node_id>\w+)/$', views.PreprintDetail.as_view(), name=views.PreprintDetail.view_name),
    url(r'^(?P<node_id>\w+)/relationships/preprint_providers/$', views.PreprintToPreprintProviderRelationship.as_view(), name=views.PreprintToPreprintProviderRelationship.view_name),
    url(r'^(?P<node_id>\w+)/preprint_providers/$', views.PreprintPreprintProvidersList.as_view(), name=views.PreprintPreprintProvidersList.view_name),
]
