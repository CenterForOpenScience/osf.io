from django.conf.urls import url

from api.identifiers import views

urlpatterns = [
    url(r'^(?P<identifier_id>\w+)/$', views.IdentifierDetail.as_view(), name=views.IdentifierDetail.view_name),
]
