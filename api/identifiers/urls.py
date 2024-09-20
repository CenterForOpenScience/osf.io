from django.urls import re_path

from api.identifiers import views

app_name = 'osf'

urlpatterns = [
    re_path(r'^(?P<identifier_id>\w+)/$', views.IdentifierDetail.as_view(), name=views.IdentifierDetail.view_name),
    re_path(r'^(?P<node_id>\w+)/identifiers/$', views.IdentifierList.as_view(), name=views.IdentifierList.view_name),
]
