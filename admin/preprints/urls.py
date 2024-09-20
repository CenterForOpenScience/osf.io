from django.urls import re_path
from admin.preprints import views

app_name = 'admin'

urlpatterns = [
    re_path(r'^$', views.PreprintSearchView.as_view(), name='search'),
    re_path(r'^flagged_spam$', views.PreprintFlaggedSpamList.as_view(), name='flagged-spam'),
    re_path(r'^known_spam$', views.PreprintKnownSpamList.as_view(), name='known-spam'),
    re_path(r'^known_ham$', views.PreprintKnownHamList.as_view(), name='known-ham'),
    re_path(r'^withdrawal_requests$', views.PreprintWithdrawalRequestList.as_view(), name='withdrawal-requests'),
    re_path(r'^(?P<guid>[a-z0-9]+)/$', views.PreprintView.as_view(), name='preprint'),
    re_path(r'^(?P<guid>[a-z0-9]+)/change_provider/$', views.PreprintProviderChangeView.as_view(), name='preprint-provider'),
    re_path(r'^(?P<guid>[a-z0-9]+)/machine_state/$', views.PreprintMachineStateView.as_view(), name='preprint-machine-state'),
    re_path(r'^(?P<guid>[a-z0-9]+)/reindex_share_preprint/$', views.PreprintReindexShare.as_view(),
        name='reindex-share-preprint'),
    re_path(r'^(?P<guid>[a-z0-9]+)/remove_user/(?P<user_id>[a-z0-9]+)/$', views.PreprintRemoveContributorView.as_view(),
        name='remove-user'),
    re_path(r'^(?P<guid>[a-z0-9]+)/make_private/$', views.PreprintMakePrivate.as_view(), name='make-private'),
    re_path(r'^(?P<guid>[a-z0-9]+)/make_public/$', views.PreprintMakePublic.as_view(), name='make-public'),
    re_path(r'^(?P<guid>[a-z0-9]+)/remove/$', views.PreprintDeleteView.as_view(), name='remove'),
    re_path(r'^(?P<guid>[a-z0-9]+)/restore/$', views.PreprintDeleteView.as_view(), name='restore'),
    re_path(r'^(?P<guid>[a-z0-9]+)/confirm_unflag/$', views.PreprintConfirmUnflagView.as_view(), name='confirm-unflag'),
    re_path(r'^(?P<guid>[a-z0-9]+)/confirm_spam/$', views.PreprintConfirmSpamView.as_view(), name='confirm-spam'),
    re_path(r'^(?P<guid>[a-z0-9]+)/confirm_ham/$', views.PreprintConfirmHamView.as_view(), name='confirm-ham'),
    re_path(r'^(?P<guid>[a-z0-9]+)/reindex_elastic_preprint/$', views.PreprintReindexElastic.as_view(),
        name='reindex-elastic-preprint'),
    re_path(r'^(?P<guid>[a-z0-9]+)/approve_withdrawal/$', views.PreprintApproveWithdrawalRequest.as_view(),
        name='approve-withdrawal'),
    re_path(r'^(?P<guid>[a-z0-9]+)/reject_withdrawal/$', views.PreprintRejectWithdrawalRequest.as_view(),
        name='reject-withdrawal'),
]
