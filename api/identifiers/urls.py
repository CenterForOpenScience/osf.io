from django.conf.urls import url

from api.nodes import views

urlpatterns = [
    url(r'^(?P<node_identifier>\w+)/$', views.IdentifierDetail.as_view(), name=views.IdentifierDetail.view_name),
]