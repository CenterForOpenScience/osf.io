import factory

from admin.common_auth.models import MyUser


class UserFactory(factory.Factory):
    FACTORY_FOR = MyUser

    id = 123
    email = 'cello@email.org'
    first_name = 'Yo-yo'
    last_name = 'Ma'
