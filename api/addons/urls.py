from django.urls import re_path

from api.addons import views

app_name = 'osf'

urlpatterns = [
    # Examples:
    # re_path(r'^$', 'api.views.home', name='home'),
    # re_path(r'^blog/', include('blog.urls')),
    re_path(r'^$', views.AddonList.as_view(), name=views.AddonList.view_name),
]
