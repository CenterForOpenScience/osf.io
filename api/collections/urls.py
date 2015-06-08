from django.conf.urls import url
from api.collections import views

urlpatterns = [
    # Examples:
    # url(r'^$', 'api.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),
    url(r'^$', views.CollectionList.as_view(), name='collection-list'),
    url(r'^$/dashboard', views.DashboardDetail.as_view(), name='dashboard-detail'),
    url(r'^(?P<pk>\w+)/$', views.CollectionDetail.as_view(), name='collection-detail'),
    url(r'^(?P<pk>\w+)/children/$', views.CollectionChildrenList.as_view(), name='collection-children'),
    url(r'^(?P<pk>\w+)/pointers/$', views.CollectionPointersList.as_view(), name='collection-pointers'),
    url(r'^(?P<pk>\w+)/pointers/(?P<pointer_id>\w+)', views.CollectionPointerDetail.as_view(),
        name='collection-pointer-detail'),
]
