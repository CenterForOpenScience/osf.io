# -*- coding: utf-8 -*-

# dummy institution model
# Some 'if' statements expect this ID to evaluate to false,
# so it should not be a number other than 0.
MAGIC_INSTITUTION_ID = 0

class RdmPermissionMixin(object):

    @property
    def is_authenticated(self):
        """determine whether the user is logged in or not"""
        return self.request.user.is_authenticated

    @property
    def is_super_admin(self):
        """determine whether the user is super or not"""
        user = self.request.user
        if not (user.is_active and user.is_registered):
            # invalid user
            return False
        if user.is_superuser:
            return True
        return False

    @property
    def is_admin(self):
        """determine whether the user is an institution administrator"""
        user = self.request.user
        if not (user.is_active and user.is_registered):
            # invalid user
            return False
        if user.is_staff and not user.is_superuser:
            return True
        return False

    def is_affiliated_institution(self, institution_id):
        """determine whether the user has affiliated institutions"""
        user = self.request.user
        if not user.affiliated_institutions.exists():
            if institution_id:
                return False
            return True
        return user.affiliated_institutions.filter(pk=institution_id).exists()

    def has_auth(self, institution_id):
        """determine whether the user has institution permissions"""
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
    """get the institutionID for the institution the user belongs to"""
    if user.affiliated_institutions.exists():
        return user.affiliated_institutions.first().id
    return None

def get_dummy_institution():
    """if the user doesn't belong to an institution, get the dummy institution model"""
    class DummyInstitution(object):
        pass
    dummy_institution = DummyInstitution()
    dummy_institution.id = MAGIC_INSTITUTION_ID
    dummy_institution.name = ''
    return dummy_institution
