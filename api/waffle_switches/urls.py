from django.conf.urls import url
from . import views


urlpatterns = [
    url(r'^$', views.WaffleSwitchList.as_view(), name=views.WaffleSwitchList.view_name),
]
