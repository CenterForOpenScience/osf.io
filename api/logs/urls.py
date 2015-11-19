from django.conf.urls import url

from api.logs import views

urlpatterns = [
    url(r'^(?P<log_id>\w+)/nodes/$', views.LogNodeList.as_view(), name='log-nodes'),
]
