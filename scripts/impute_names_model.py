"""
Impute name parts for all existing users.
"""

from framework.auth.utils import impute_names

from website.app import init_app
from website import models

app = init_app('website.settings', set_backends=True, routes=True)

def impute_names():

    for user in models.User.find():

        parsed = impute_names(user.fullname)
        for field, value in parsed.items():
            if getattr(user, field, None) is None:
                setattr(user, field, value)
        user.save()

if __name__ == '__main__':
    impute_names()
