from django.conf.urls import url

from api.revisions import views

app_name = 'osf'

urlpatterns = [
    url(
        r'^$', views.SchemaResponsesList.as_view(), name=views.SchemaResponsesList.view_name,
    ),
    url(
        r'^(?P<revision_id>\w+)/$',
        views.SchemaResponsesDetail.as_view(),
        name=views.SchemaResponsesDetail.view_name,
    ),
]