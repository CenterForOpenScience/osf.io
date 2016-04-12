from django.conf.urls import url

from api.guid import views

urlpatterns = [
    url(r'^(?P<guid>\w+)/$', views.GuidRedirect.as_view(), name=views.GuidRedirect.view_name),
]
