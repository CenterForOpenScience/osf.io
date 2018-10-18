from django.conf.urls import url
from admin.preprints import views

app_name = 'admin'

urlpatterns = [
    url(r'^$', views.PreprintFormView.as_view(), name='search'),
    url(r'^(?P<guid>[a-z0-9]+)/$', views.PreprintView.as_view(), name='preprint'),
    url(r'^(?P<guid>[a-z0-9]+)/reindex_share_preprint/$', views.PreprintReindexShare.as_view(),
        name='reindex-share-preprint'),
    url(r'^(?P<guid>[a-z0-9]+)/remove_user/(?P<user_id>[a-z0-9]+)/$',
        views.PreprintRemoveContributorView.as_view(), name='remove_user'),
    url(r'^(?P<guid>[a-z0-9]+)/remove/$', views.PreprintDeleteView.as_view(),
        name='remove'),
    url(r'^(?P<guid>[a-z0-9]+)/restore/$', views.PreprintDeleteView.as_view(),
        name='restore'),
    url(r'^(?P<guid>[a-z0-9]+)/confirm_spam/$', views.PreprintConfirmSpamView.as_view(),
        name='confirm-spam'),
    url(r'^(?P<guid>[a-z0-9]+)/confirm_ham/$', views.PreprintConfirmHamView.as_view(),
        name='confirm-ham'),
    url(r'^(?P<guid>[a-z0-9]+)/reindex_elastic_preprint/$', views.PreprintReindexElastic.as_view(),
        name='reindex-elastic-preprint'),
    url(r'^(?P<guid>[a-z0-9]+)/approve_withdrawal/$', views.PreprintApproveWithdrawalRequest.as_view(),
        name='approve-withdrawal'),
    url(r'^(?P<guid>[a-z0-9]+)/reject_withdrawal/$', views.PreprintRejectWithdrawalRequest.as_view(),
        name='reject-withdrawal'),
    url(r'^flagged_spam$', views.PreprintFlaggedSpamList.as_view(), name='flagged-spam'),
    url(r'^known_spam$', views.PreprintKnownSpamList.as_view(), name='known-spam'),
    url(r'^known_ham$', views.PreprintKnownHamList.as_view(), name='known-ham'),
    url(r'^withdrawal_requests$', views.PreprintWithdrawalRequestList.as_view(), name='withdrawal-requests'),
]
