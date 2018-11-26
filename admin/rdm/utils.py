# -*- coding: utf-8 -*-

# dummi institution model
# If there is a code that assumes False in the evaluation of the sentence,
# it should not be a number other than 0.
MAGIC_INSTITUTION_ID = 0

class RdmPermissionMixin(object):

    @property
    def is_authenticated(self):
        """login check"""
        return self.request.user.is_authenticated

    @property
    def is_super_admin(self):
        """superuser check"""
        user = self.request.user
        if not (user.is_active and user.is_registered):
            # 無効なユーザ
            return False
        if user.is_superuser:
            return True
        return False

    @property
    def is_admin(self):
        """institution administrator check"""
        user = self.request.user
        if not (user.is_active and user.is_registered):
            # invalid user
            return False
        if user.is_staff and not user.is_superuser:
            return True
        return False

    def is_affiliated_institution(self, institution_id):
        """check institution user belonging"""
        user = self.request.user
        if not user.affiliated_institutions.exists():
            if institution_id:
                return False
            return True
        return user.affiliated_institutions.filter(pk=institution_id).exists()

    def has_auth(self, institution_id):
        """check permissions to institution"""
        # login check
        if not self.is_authenticated:
            return False
        # allowed if superuser
        if self.is_super_admin:
            return True
        elif self.is_admin:
            return self.is_affiliated_institution(institution_id)
        return False

def get_institution_id(user):
    """get institutionID at user is belonging"""
    if user.affiliated_institutions.exists():
        return user.affiliated_institutions.first().id
    return None

def get_dummy_institution():
    """get dummy institution model if user is not belonging to institution"""
    class DummyInstitution(object):
        pass
    dummy_institution = DummyInstitution()
    dummy_institution.id = MAGIC_INSTITUTION_ID
    dummy_institution.name = ''
    return dummy_institution
