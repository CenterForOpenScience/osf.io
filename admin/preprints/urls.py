from django.conf.urls import url
from admin.preprints import views

app_name = 'admin'

urlpatterns = [
    url(r'^$', views.PreprintFormView.as_view(), name='search'),
    url(r'^(?P<guid>[a-z0-9]+)/$', views.PreprintView.as_view(), name='preprint'),
    url(r'^(?P<guid>[a-z0-9]+)/reindex_share_preprint/$', views.PreprintReindexShare.as_view(),
        name='reindex-share-preprint'),
]
