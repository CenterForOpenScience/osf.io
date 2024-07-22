from django.urls import re_path

from api.search import views

app_name = 'osf'

urlpatterns = [
    re_path(r'^$', views.Search.as_view(), name=views.Search.view_name),
    re_path(r'^components/$', views.SearchComponents.as_view(), name=views.SearchComponents.view_name),
    re_path(r'^files/$', views.SearchFiles.as_view(), name=views.SearchFiles.view_name),
    re_path(r'^projects/$', views.SearchProjects.as_view(), name=views.SearchProjects.view_name),
    re_path(r'^registrations/$', views.SearchRegistrations.as_view(), name=views.SearchRegistrations.view_name),
    re_path(r'^users/$', views.SearchUsers.as_view(), name=views.SearchUsers.view_name),
    re_path(r'^institutions/$', views.SearchInstitutions.as_view(), name=views.SearchInstitutions.view_name),
    re_path(r'^collections/$', views.SearchCollections.as_view(), name=views.SearchCollections.view_name),

    # not currently supported by v1, but should be supported by v2
    # re_path(r'^nodes/$', views.SearchProjects.as_view(), name=views.SearchProjects.view_name),
]
