from django.urls import re_path

from api.search import views

app_name = 'osf'

urlpatterns = [
    re_path(r'^collections/$', views.SearchCollections.as_view(), name=views.SearchCollections.view_name),

    # not currently supported by v1, but should be supported by v2
    # re_path(r'^nodes/$', views.SearchProjects.as_view(), name=views.SearchProjects.view_name),
]
