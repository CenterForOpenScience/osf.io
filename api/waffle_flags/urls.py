from django.conf.urls import url
from . import views


urlpatterns = [
    url(r'^$', views.WaffleFlagList.as_view(), name=views.WaffleFlagList.view_name),
    url(r'^(?P<name>\w+)/$', views.WaffleFlagDetail.as_view(), name=views.WaffleFlagDetail.view_name),

]
