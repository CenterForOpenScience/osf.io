from django.conf.urls import url

from api.media import views

app_name = 'osf'

urlpatterns = [
    url(r'^(?P<filename>[^/]+)$', views.get_media, name='get_media'),
]
