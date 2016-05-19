from django.conf.urls import url

from api.identifiers import views

urlpatterns = [
    url(r'^(?P<node_identifier>.+)/$', views.IdentifierDetail.as_view(), name=views.IdentifierDetail.view_name),
]
