from django.http import Http404

from admin.user_identification_information.views import (
    UserIdentificationInformationListView,
    UserIdentificationListViewListView,
    UserIdentificationDetailView,
)


class UserIdentificationInformationListViewAdminView(UserIdentificationInformationListView):

    def get_context_data(self, **kwargs):
        if self.is_super_admin:
            raise Http404('Page not found')
        return super(UserIdentificationInformationListView, self).get_context_data(**kwargs)


class UserIdentificationListAdminView(UserIdentificationListViewListView):

    def get_user_list(self):
        if self.is_super_admin:
            raise Http404('Page not found')
        return self.user_list()


class UserIdentificationDetailAdminView(UserIdentificationDetailView):

    def get_object(self):
        if self.is_super_admin:
            raise Http404('Page not found')
        return self.user_details()
