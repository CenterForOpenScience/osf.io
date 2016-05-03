from framework.auth import User as MODMUser
from osf_models.models import User
from osf_models.scripts.load_nodes import get_or_create_user
from website.app import init_app


def main():
    total = MODMUser.find().count()
    count = 0
    page_size = 1000

    while count < total:
        modm_users = MODMUser.find()[count:count + page_size]
        for modm_user in modm_users:
            django_user = get_or_create_user(modm_user)
            count += 1
        print 'Count: {}'.format(count)
