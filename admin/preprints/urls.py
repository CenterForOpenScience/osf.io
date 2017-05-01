from django.conf.urls import url
from admin.preprints import views


urlpatterns = [
    url(r'^$', views.PreprintFormView.as_view(), name='search'),
    url(r'^(?P<guid>[a-z0-9]+)/$', views.PreprintView.as_view(), name='preprint'),
]
