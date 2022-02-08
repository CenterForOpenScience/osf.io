from django.conf.urls import url
from admin.schema_responses import views

app_name = 'admin'

urlpatterns = [
    url(r'^(?P<schema_response_id>[a-z0-9]+)/$', views.SchemaResponseDetailView.as_view(), name='detail'),
    url(r'^$', views.SchemaResponseListView.as_view(), name='list'),
]
