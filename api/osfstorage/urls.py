from django.conf.urls import url

from api.osfstorage import views

urlpatterns = [
    url(r'^$', views.OsfStorageList.as_view(), name=views.OsfStorageList.view_name),
]
