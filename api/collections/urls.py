from django.conf.urls import url
from api.collections import views

urlpatterns = [
    # Examples:
    # url(r'^$', 'api.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),
    url(r'^$', views.CollectionList.as_view(), name='collection-list'),
    url(r'^(?P<collection_id>\w+)/$', views.CollectionDetail.as_view(), name='collection-detail'),
    url(r'^(?P<collection_id>\w+)/children/$', views.CollectionChildrenList.as_view(), name='collection-children'),
    url(r'^(?P<collection_id>\w+)/pointers/$', views.CollectionPointersList.as_view(), name='collection-pointers'),
    url(r'^(?P<collection_id>\w+)/pointers/(?P<pointer_id>\w+)/$', views.CollectionPointerDetail.as_view(),
        name='collection-pointer-detail'),
]
