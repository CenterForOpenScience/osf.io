from django.conf.urls import url
from admin.registration_schemas import views

app_name = 'admin'

urlpatterns = [
    url(r'^(?P<registration_schema_id>[a-z0-9]+)/$', views.RegistrationSchemaDetailView.as_view(), name='detail'),
    url(r'^$', views.RegistrationSchemaListView.as_view(), name='list'),
]
