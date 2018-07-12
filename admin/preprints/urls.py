from django.conf.urls import url
from admin.preprints import views

app_name = 'admin'

urlpatterns = [
    url(r'^$', views.PreprintFormView.as_view(), name='search'),
    url(r'^(?P<guid>[a-z0-9]+)/$', views.PreprintView.as_view(), name='preprint'),
    url(r'^(?P<guid>[a-z0-9]+)/reindex_share_preprint/$', views.PreprintReindexShare.as_view(),
        name='reindex-share-preprint'),
    url(r'^(?P<guid>[a-z0-9]+)/confirm_spam/$', views.PreprintConfirmSpamView.as_view(),
        name='confirm-spam'),
    url(r'^(?P<guid>[a-z0-9]+)/confirm_ham/$', views.PreprintConfirmHamView.as_view(),
        name='confirm-ham'),
    url(r'^flagged_spam$', views.PreprintFlaggedSpamList.as_view(), name='flagged-spam'),
    url(r'^known_spam$', views.PreprintKnownSpamList.as_view(), name='known-spam'),
    url(r'^known_ham$', views.PreprintKnownHamList.as_view(), name='known-ham'),
]
