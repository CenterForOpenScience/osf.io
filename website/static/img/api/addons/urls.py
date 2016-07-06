from django.conf.urls import url

from api.addons import views

urlpatterns = [
    # Examples:
    # url(r'^$', 'api.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),
    url(r'^$', views.AddonList.as_view(), name=views.AddonList.view_name),
]
