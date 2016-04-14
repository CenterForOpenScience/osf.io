from django.conf.urls import url

from api.guids import views

urlpatterns = [
    url(r'^(?P<guids>\w+)/$', views.GuidRedirect.as_view(), name=views.GuidRedirect.view_name),
]
