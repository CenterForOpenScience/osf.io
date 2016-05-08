import factory

from admin.common_auth.models import MyUser


class UserFactory(factory.Factory):
    class Meta:
        model = MyUser

    id = 123
    email = 'cello@email.org'
    first_name = 'Yo-yo'
    last_name = 'Ma'
    osf_id = 'abc12'

    @classmethod
    def is_in_group(cls, value):
        return True
