from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^review_logs/$', views.LogList.as_view(), name=views.LogList.view_name),
    url(r'^review_logs/(?P<log_id>\w+)/$', views.LogDetail.as_view(), name=views.LogDetail.view_name),
    url(r'^setup/(?P<provider_id>\w+)/$', views.SetUpProvider.as_view(), name=views.SetUpProvider.view_name),
]
