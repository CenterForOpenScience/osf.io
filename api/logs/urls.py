from django.conf.urls import url

from api.logs import views

urlpatterns = [
    url(r'^(?P<log_id>\w+)/$', views.NodeLogDetail.as_view(), name=views.NodeLogDetail.view_name),
    url(r'^(?P<log_id>\w+)/nodes/$', views.LogNodeList.as_view(), name=views.LogNodeList.view_name),
]
