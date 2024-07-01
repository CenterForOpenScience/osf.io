from django.urls import re_path
from admin.registration_schemas import views

app_name = 'admin'

urlpatterns = [
    re_path(r'^create/$', views.RegistrationSchemaCreateView.as_view(), name='create'),
    re_path(r'^(?P<registration_schema_id>[a-z0-9]+)/$', views.RegistrationSchemaDetailView.as_view(), name='detail'),
    re_path(r'^(?P<registration_schema_id>[a-z0-9]+)/delete/$$', views.RegistrationSchemaDeleteView.as_view(), name='remove'),
    re_path(r'^$', views.RegistrationSchemaListView.as_view(), name='list'),
]
