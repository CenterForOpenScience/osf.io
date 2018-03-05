from django.conf.urls import url

from api.subscriptions import views

app_name = 'osf'

urlpatterns = [
    # Examples:
    # url(r'^$', 'api.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),
    url(r'^$', views.UserProviderSubscriptionList.as_view(), name=views.UserProviderSubscriptionList.view_name),
    url(r'^(?P<subscription_id>\w+)/$', views.UserProviderSubscriptionDetail.as_view(), name=views.UserProviderSubscriptionDetail.view_name),
]
