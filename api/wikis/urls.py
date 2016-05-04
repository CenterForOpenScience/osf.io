from django.conf.urls import url
from api.wikis import views


urlpatterns = [
    url(r'^(?P<wiki_id>\w+)/$', views.WikiDetail.as_view(), name=views.WikiDetail.view_name),
]
