from django.http import Http404

from admin.user_identification_information.views import (
    UserIdentificationInformation,
    UserIdentificationList,
    UserIdentificationDetails,
    ExportFileCSV,
)


class UserIdentificationInformationAdminView(UserIdentificationInformation):

    def get_context_data(self, **kwargs):
        if self.is_super_admin:
            raise Http404('Page not found')
        return super(UserIdentificationInformation, self).get_context_data(**kwargs)


class UserIdentificationListAdminView(UserIdentificationList):

    def get_userlist(self):
        if self.is_super_admin:
            raise Http404('Page not found')
        return self.user_list()


class UserIdentificationDetailsAdminView(UserIdentificationDetails):

    def get_object(self):
        if self.is_super_admin:
            raise Http404('Page not found')
        return self.user_details()


class ExportFileCSVAdminView(ExportFileCSV):
    pass
