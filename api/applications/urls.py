from django.conf.urls import url

from api.applications import views

urlpatterns = [
    url(r'^$', views.ApplicationList.as_view(), name=views.ApplicationList.view_name),
    url(r'^(?P<client_id>\w+)/$', views.ApplicationDetail.as_view(), name=views.ApplicationDetail.view_name)
]
