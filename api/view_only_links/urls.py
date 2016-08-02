from django.conf.urls import url

from api.view_only_links import views

urlpatterns = [
    url(r'^(?P<link_id>\w+)/$', views.ViewOnlyLinkDetail.as_view(), name=views.ViewOnlyLinkDetail.view_name),
]
