from modularodm import fields
from modularodm import Q
from modularodm.exceptions import NoResultsFound

from framework.mongo import ObjectId
from framework.mongo import StoredObject

from website.admin import ROLE_TYPES, GROUPS, SUPER

def in_role_types(role):
    return not role or role in ROLE_TYPES

def in_groups(group):
    return not group or group in GROUPS

class Role(StoredObject):

    _id = fields.StringField(primary=True, default=lambda: str(ObjectId()))

    owner = fields.ForeignField('user')

    group = fields.StringField(default=None)
    role_type = fields.StringField(default=None, validate=in_role_types)

    @staticmethod
    def for_user(user, group):
        query = Q('owner', 'eq', user) & Q('group', 'eq', group)
        try:
            return Role.find_one(query)
        except NoResultsFound:
            return None

    @property
    def is_super(self):
        return self.role_type == SUPER
