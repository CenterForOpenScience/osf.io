from django.urls import re_path
from api.wikis import views

app_name = 'osf'

urlpatterns = [
    re_path(r'^(?P<wiki_id>\w+)/$', views.WikiDetail.as_view(), name=views.WikiDetail.view_name),
    re_path(r'^(?P<wiki_id>\w+)/content/$', views.WikiContent.as_view(), name=views.WikiContent.view_name),
    re_path(r'^(?P<wiki_id>\w+)/versions/$', views.WikiVersions.as_view(), name=views.WikiVersions.view_name),
    re_path(r'^(?P<wiki_id>\w+)/versions/(?P<version_id>\w+)/$', views.WikiVersionDetail.as_view(), name=views.WikiVersionDetail.view_name),
    re_path(r'^(?P<wiki_id>\w+)/versions/(?P<version_id>\w+)/content/$', views.WikiVersionContent.as_view(), name=views.WikiVersionContent.view_name),
]
