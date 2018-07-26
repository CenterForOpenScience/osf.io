from django.conf.urls import url
from . import views

urlpatterns = [
    url(r'^$', views.DismissedAlertList.as_view(), name=views.DismissedAlertList.view_name),
    url(r'^(?P<_id>\w+)/$', views.DismissedAlertDetail.as_view(), name=views.DismissedAlertDetail.view_name),
]
