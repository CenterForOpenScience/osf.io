from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^dash_board$', views.dashboard, name='dashboard'),
    url(r'^user_session_info', views.user_session, name='dashboard'),
    url(r'^product_usage', views.product_usage, name='product_usage'),
]
