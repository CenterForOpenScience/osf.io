from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.UserFormView.as_view(),
        name='search'),
    url(r'^flagged_spam$', views.UserFlaggedSpamList.as_view(),
        name='flagged-spam'),
    url(r'^known_spam$', views.UserKnownSpamList.as_view(),
        name='known-spam'),
    url(r'^known_ham$', views.UserKnownHamList.as_view(),
        name='known-ham'),
    url(r'^workshop$', views.UserWorkshopFormView.as_view(),
        name='workshop'),
    url(r'^(?P<guid>[a-z0-9]+)/$', views.UserView.as_view(),
        name='user'),
    url(r'^(?P<guid>[a-z0-9]+)/reset-password/$',
        views.ResetPasswordView.as_view(),
        name='reset_password'),
    url(r'^(?P<guid>[a-z0-9]+)/disable/$', views.UserDeleteView.as_view(),
        name='disable'),
    url(r'^(?P<guid>[a-z0-9]+)/disable_spam/$', views.SpamUserDeleteView.as_view(),
        name='spam_disable'),
    url(r'^(?P<guid>[a-z0-9]+)/enable_ham/$', views.HamUserRestoreView.as_view(),
        name='ham_enable'),
    url(r'^(?P<guid>[a-z0-9]+)/reactivate/$', views.UserDeleteView.as_view(),
        name='reactivate'),
    url(r'^(?P<guid>[a-z0-9]+)/two-factor/disable/$',
        views.User2FactorDeleteView.as_view(),
        name='remove2factor'),
]
