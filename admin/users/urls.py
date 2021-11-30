from django.conf.urls import url

from . import views

app_name = 'admin'

urlpatterns = [
    url(r'^$', views.UserSearchView.as_view(), name='search'),
    url(r'^flagged_spam$', views.UserFlaggedSpamList.as_view(), name='flagged-spam'),
    url(r'^known_spam$', views.UserKnownSpamList.as_view(), name='known-spam'),
    url(r'^known_ham$', views.UserKnownHamList.as_view(), name='known-ham'),
    url(r'^workshop$', views.UserWorkshopFormView.as_view(), name='workshop'),
    url(r'^(?P<guid>[a-z0-9]+)/$', views.UserView.as_view(), name='user'),
    url(r'^search/(?P<name>.*)/$', views.UserSearchList.as_view(), name='search_list'),
    url(r'^(?P<guid>[a-z0-9]+)/reset-password/$', views.ResetPasswordView.as_view(), name='reset_password'),
    url(r'^(?P<guid>[a-z0-9]+)/gdpr_delete/$', views.UserGDPRDeleteView.as_view(), name='GDPR_delete'),
    url(r'^(?P<guid>[a-z0-9]+)/disable/$', views.UserDeleteView.as_view(), name='disable'),
    url(r'^(?P<guid>[a-z0-9]+)/disable_spam/$', views.SpamUserView.as_view(), name='spam_disable'),
    url(r'^(?P<guid>[a-z0-9]+)/enable_ham/$', views.HamUserRestoreView.as_view(), name='ham_enable'),
    url(r'^(?P<guid>[a-z0-9]+)/reactivate/$', views.UserDeleteView.as_view(), name='reactivate'),
    url(r'^(?P<guid>[a-z0-9]+)/get_claim_urls/$', views.GetUserClaimLinks.as_view(), name='get_claim_urls'),
    url(r'^(?P<guid>[a-z0-9]+)/two-factor/disable/$', views.User2FactorDeleteView.as_view(), name='remove2factor'),
    url(r'^(?P<guid>[a-z0-9]+)/system_tags/add/$', views.UserAddSystemTag.as_view(), name='add_system_tag'),
    url(r'^(?P<guid>[a-z0-9]+)/get_confirmation/$', views.GetUserConfirmationLink.as_view(), name='get_confirmation'),
    url(r'^(?P<guid>[a-z0-9]+)/get_reset_password/$', views.GetPasswordResetLink.as_view(), name='get_reset_password'),
    url(r'^(?P<guid>[a-z0-9]+)/reindex_elastic_user/$', views.UserReindexElastic.as_view(), name='reindex-elastic-user'),
    url(r'^(?P<guid>[a-z0-9]+)/merge_accounts/$', views.UserMergeAccounts.as_view(), name='merge-accounts'),
]
