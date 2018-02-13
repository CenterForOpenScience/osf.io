from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^(?P<request_id>\w+)/$', views.NodeRequestDetail.as_view(), name=views.NodeRequestDetail.view_name),
]
