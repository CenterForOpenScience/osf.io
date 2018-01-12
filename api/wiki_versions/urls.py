from django.conf.urls import url
from api.wiki_versions import views

app_name = 'osf'

urlpatterns = [
    url(r'^(?P<wiki_version_id>\w+)/$', views.WikiVersionDetail.as_view(), name=views.WikiVersionDetail.view_name),
]
