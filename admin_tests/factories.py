import factory

from osf.models import AdminProfile
from osf_tests.factories import UserFactory as OSFUserFactory


class UserFactory(factory.Factory):
    class Meta:
        model = AdminProfile

    user = OSFUserFactory

    desk_token = 'el-p'
    test_token_secret = 'mike'

    @classmethod
    def is_in_group(cls, value):
        return True
