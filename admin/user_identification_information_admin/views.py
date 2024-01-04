from osf.models import OSFUser

from admin.user_identification_information.views import (
    UserIdentificationListView,
    UserIdentificationDetailView,
    ExportFileCSVView,
)


class UserIdentificationAdminListView(UserIdentificationListView):
    def test_func(self):
        """check user permissions"""
        # login check
        if not self.is_authenticated:
            return False

        # permitted if is admin and login user has institution
        return not self.is_super_admin and self.is_admin \
            and self.request.user.affiliated_institutions.exists()

    def get_user_list(self):
        return self.user_list()


class UserIdentificationDetailAdminView(UserIdentificationDetailView):
    def test_func(self):
        """check user permissions"""
        # login check
        if not self.is_authenticated:
            return False

        # permitted if is admin and login user has institution
        if not self.is_super_admin and self.is_admin \
         and self.request.user.affiliated_institutions.exists():
            user_detail = OSFUser.load(self.kwargs.get('guid'))
            return self.has_auth(user_detail.affiliated_institutions.first().id)
        else:
            return False

    def get_object(self):
        return self.user_details()


class ExportFileCSVAdminView(ExportFileCSVView):

    def test_func(self):
        """check user permissions"""
        # login check
        if not self.is_authenticated:
            return False

        # permitted if is admin and login user has institution
        return not self.is_super_admin and self.is_admin \
            and self.request.user.affiliated_institutions.exists()

    pass
