from django.conf.urls import url

from api.nodes import views

urlpatterns = [
    url(r'^(?P<node_identifier>.+)/$', views.NodeIdentifierDetail.as_view(), name=views.NodeIdentifierDetail.view_name),
]