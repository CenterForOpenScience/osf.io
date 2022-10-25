from django.conf.urls import re_path

from api.collections import views

app_name = 'osf'

urlpatterns = [
    re_path(r'^$', views.CollectionList.as_view(), name=views.CollectionList.view_name),
    re_path(r'^(?P<collection_id>\w+)/$', views.CollectionDetail.as_view(), name=views.CollectionDetail.view_name),
    re_path(r'^(?P<collection_id>\w+)/collected_metadata/$', views.CollectedMetaList.as_view(), name=views.CollectedMetaList.view_name),
    re_path(r'^(?P<collection_id>\w+)/collected_metadata/(?P<cgm_id>\w+)/$', views.CollectedMetaDetail.as_view(), name=views.CollectedMetaDetail.view_name),
    re_path(r'^(?P<collection_id>\w+)/collected_metadata/(?P<cgm_id>\w+)/subjects/$', views.CollectedMetaSubjectsList.as_view(), name=views.CollectedMetaSubjectsList.view_name),
    re_path(r'^(?P<collection_id>\w+)/collected_metadata/(?P<cgm_id>\w+)/relationships/subjects/$', views.CollectedMetaSubjectsRelationship.as_view(), name=views.CollectedMetaSubjectsRelationship.view_name),
    re_path(r'^(?P<collection_id>\w+)/linked_nodes/$', views.LinkedNodesList.as_view(), name=views.LinkedNodesList.view_name),
    re_path(r'^(?P<collection_id>\w+)/linked_preprints/$', views.LinkedPreprintsList.as_view(), name=views.LinkedPreprintsList.view_name),
    re_path(r'^(?P<collection_id>\w+)/linked_registrations/$', views.LinkedRegistrationsList.as_view(), name=views.LinkedRegistrationsList.view_name),
    re_path(r'^(?P<collection_id>\w+)/node_links/$', views.NodeLinksList.as_view(), name=views.NodeLinksList.view_name),
    re_path(r'^(?P<collection_id>\w+)/node_links/(?P<node_link_id>\w+)/', views.NodeLinksDetail.as_view(), name=views.NodeLinksDetail.view_name),
    re_path(r'^(?P<collection_id>\w+)/relationships/linked_nodes/$', views.CollectionLinkedNodesRelationship.as_view(), name=views.CollectionLinkedNodesRelationship.view_name),
    re_path(r'^(?P<collection_id>\w+)/relationships/linked_preprints/$', views.CollectionLinkedPreprintsRelationship.as_view(), name=views.CollectionLinkedPreprintsRelationship.view_name),
    re_path(r'^(?P<collection_id>\w+)/relationships/linked_registrations/$', views.CollectionLinkedRegistrationsRelationship.as_view(), name=views.CollectionLinkedRegistrationsRelationship.view_name),
]
