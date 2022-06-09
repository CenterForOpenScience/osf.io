from django.conf.urls import url
from admin.registration_schemas import views

app_name = 'admin'

urlpatterns = [
    url(r'^create/$', views.RegistrationSchemaCreateView.as_view(), name='create'),
    url(r'^(?P<registration_schema_id>[a-z0-9]+)/$', views.RegistrationSchemaDetailView.as_view(), name='detail'),
    url(r'^(?P<registration_schema_id>[a-z0-9]+)/delete/$$', views.RegistrationSchemaDeleteView.as_view(), name='remove'),
    url(r'^$', views.RegistrationSchemaListView.as_view(), name='list'),
]
