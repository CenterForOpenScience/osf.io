from django.conf.urls import re_path

from api.subscriptions import views

app_name = 'osf'

urlpatterns = [
    re_path(r'^$', views.SubscriptionList.as_view(), name=views.SubscriptionList.view_name),
    re_path(r'^(?P<subscription_id>\w+)/$', views.SubscriptionDetail.as_view(), name=views.SubscriptionDetail.view_name),
]
