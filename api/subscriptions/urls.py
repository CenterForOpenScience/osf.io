from django.conf.urls import url

from api.subscriptions import views

app_name = 'osf'

urlpatterns = [
    # Examples:
    # url(r'^$', 'api.views.home', name='home'),
    # url(r'^blog/', include('blog.urls')),
    url(r'^(?P<provider_id>\w+)/(?P<user_id>\w+)$', views.UserProviderSubscriptionDetail.as_view(), name=views.UserProviderSubscriptionDetail.view_name),
]
