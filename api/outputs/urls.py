from django.conf.urls import url

from api.outputs import views

app_name = 'osf'

urlpatterns = [
    url(
        r'^(?P<output_id>\w+)/$',
        views.OutputDetail.as_view(),
        name=views.OutputDetail.view_name,
    ),
]
