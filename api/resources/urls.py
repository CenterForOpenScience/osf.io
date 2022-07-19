from django.conf.urls import url

from api.resources import views

app_name = 'osf'

urlpatterns = [
    url(
        r'^(?P<resource_id>\w+)/$',
        views.ResourceDetail.as_view(),
        name=views.ResourceDetail.view_name,
    ),
]
