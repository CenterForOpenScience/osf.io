from django.conf.urls import url

from api.sparse import views

app_name = 'osf'

urlpatterns = [
    # Examples:
    # url(r'^$', 'api.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),
    url(r'^nodes/', views.SparseNodeList.as_view(), name=views.SparseNodeList.view_name),
    url(r'^users/(?P<user_id>\w+)/nodes/$', views.SparseUserNodeList.as_view(),
        name=views.SparseUserNodeList.view_name),
    url(r'^nodes/(?P<user_id>\w+)/children/$', views.SparseNodeChildrenList.as_view(),
        name=views.SparseNodeChildrenList.view_name),
    url(r'^registrations/$', views.SparseRegistrationList.as_view(), name=views.SparseRegistrationList.view_name),
    url(r'^users/(?P<user_id>\w+)/registrations/$', views.SparseUserRegistrationList.as_view(),
        name=views.SparseUserRegistrationList.view_name),
    url(r'^registrations/(?P<node_id>\w+)/children/$', views.SparseRegistrationChildrenList.as_view(),
        name=views.SparseRegistrationChildrenList.view_name),

]
