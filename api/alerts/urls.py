from django.urls import re_path
from . import views

urlpatterns = [
    re_path(r'^$', views.DismissedAlertList.as_view(), name=views.DismissedAlertList.view_name),
    re_path(r'^(?P<_id>\w+)/$', views.DismissedAlertDetail.as_view(), name=views.DismissedAlertDetail.view_name),
]
