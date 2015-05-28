from django.conf import settings
from django.conf.urls import include, url, patterns
# from django.contrib import admin
from django.conf.urls.static import static


from . import views


urlpatterns = [
    ### API ###
    url(r'^v2/', include(patterns('',
        url(r'^$', views.root),
        url(r'^nodes/', include('api.nodes.urls', namespace='nodes')),
        url(r'^users/', include('api.users.urls', namespace='users')),
        url(r'^docs/', include('rest_framework_swagger.urls')),
    )))] + static('/static/', document_root=settings.STATIC_ROOT)