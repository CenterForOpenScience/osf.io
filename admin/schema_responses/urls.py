from django.urls import re_path
from admin.schema_responses import views

app_name = 'admin'

urlpatterns = [
    re_path(r'^(?P<schema_response_id>[a-z0-9]+)/$', views.SchemaResponseDetailView.as_view(), name='detail'),
    re_path(r'^$', views.SchemaResponseListView.as_view(), name='list'),
]
