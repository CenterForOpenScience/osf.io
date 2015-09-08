from django.conf.urls import url

from api.applications import views

urlpatterns = [
    url(r'^$', views.ApplicationList.as_view(), name='application-list'),
    url(r'^(?P<client_id>\w+)/$', views.ApplicationDetail.as_view(), name='application-detail')
]
