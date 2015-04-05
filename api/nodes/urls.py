from django.conf.urls import url
from api.nodes import views as node_views

urlpatterns = [
    # Examples:
    # url(r'^$', 'api.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),
    url(r'^$', node_views.NodeList.as_view(), name='node-list'),
]
