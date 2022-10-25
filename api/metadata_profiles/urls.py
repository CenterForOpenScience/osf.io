from django.conf.urls import url

from api.metadata_profiles import views

app_name = 'osf'

urlpatterns = [
    url(r'^$', views.MetadataProfileList.as_view(), name=views.MetadataProfileList.view_name),
    url(r'^(?P<metadata_profile_id>\w+)/$', views.MetadataProfileDetail.as_view(), name=views.MetadataProfileDetail.view_name),
]
