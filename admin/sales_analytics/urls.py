from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^dashboard$', views.dashboard, name='dashboard'),
    url(r'^user_session', views.user_session, name='user_session'),
    url(r'^product_view', views.product_view, name='product_view'),
    url(r'^product_usage', views.product_usage, name='product_usage'),
    url(r'^debug_test', views.debug_test, name='debug_test'),
]
