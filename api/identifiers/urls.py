from django.conf.urls import url

from api.identifiers import views

app_name = 'osf'

urlpatterns = [
    url(r'^(?P<identifier_id>\w+)/$', views.IdentifierDetail.as_view(), name=views.IdentifierDetail.view_name),
    url(r'^(?P<node_id>\w+)/identifiers/$', views.IdentifierList.as_view(), name=views.IdentifierList.view_name),
]
