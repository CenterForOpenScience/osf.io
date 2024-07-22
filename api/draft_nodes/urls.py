from django.urls import re_path

from api.draft_nodes import views

app_name = 'osf'

urlpatterns = [
    re_path(r'^(?P<node_id>\w+)/$', views.DraftNodeDetail.as_view(), name=views.DraftNodeDetail.view_name),
    re_path(r'^(?P<node_id>\w+)/draft_registrations/$', views.DraftNodeDraftRegistrationsList.as_view(), name=views.DraftNodeDraftRegistrationsList.view_name),
    re_path(r'^(?P<node_id>\w+)/files/$', views.DraftNodeStorageProvidersList.as_view(), name=views.DraftNodeStorageProvidersList.view_name),
    re_path(r'^(?P<node_id>\w+)/files/providers/(?P<provider>\w+)/?$', views.DraftNodeStorageProviderDetail.as_view(), name=views.DraftNodeStorageProviderDetail.view_name),
    re_path(r'^(?P<node_id>\w+)/files/(?P<provider>\w+)(?P<path>/(?:.*/)?)$', views.DraftNodeFilesList.as_view(), name=views.DraftNodeFilesList.view_name),
    re_path(r'^(?P<node_id>\w+)/files/(?P<provider>\w+)(?P<path>/.+[^/])$', views.DraftNodeFileDetail.as_view(), name=views.DraftNodeFileDetail.view_name),
]
