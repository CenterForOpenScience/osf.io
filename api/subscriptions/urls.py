from django.conf.urls import url

from api.subscriptions import views

app_name = 'osf'

urlpatterns = [
    url(r'^$', views.SubscriptionList.as_view(), name=views.SubscriptionList.view_name),
    url(r'^(?P<subscription_id>\w+)/$', views.SubscriptionDetail.as_view(), name=views.SubscriptionDetail.view_name),
]
