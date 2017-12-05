from django.conf.urls import url

from api.media import views

app_name = 'osf'

urlpatterns = [
    url(r'^(?P<filename>[^/]+)$', views.FileUploadView.as_view()),
]
