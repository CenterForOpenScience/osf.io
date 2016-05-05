from django.conf.urls import url
from api.wikis import views


urlpatterns = [
    url(r'^(?P<wiki_id>\w+)/$', views.WikiDetail.as_view(), name=views.WikiDetail.view_name),
    url(r'^(?P<wiki_id>\w+)/content/$', views.WikiContent.as_view(), name=views.WikiContent.view_name),
]
