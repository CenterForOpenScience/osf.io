from django.urls import re_path

from api.logs import views

app_name = 'osf'

urlpatterns = [
    re_path(r'^(?P<log_id>\w+)/$', views.NodeLogDetail.as_view(), name=views.NodeLogDetail.view_name),
]
