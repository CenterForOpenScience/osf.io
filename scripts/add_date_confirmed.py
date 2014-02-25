"""
With email confirmation enabled, the `date_confirmed` is used to filter users
for e.g. search results. This requires setting this field for all users
registered before confirmation was added. This migration sets each user's
`date_confirmed` to his / her `date_registered`.
"""

from website.app import init_app
from website import models

app = init_app()

def add_date_confirmed():

    for user in models.User.find():
        if user.date_confirmed is None:
            user.date_confirmed = user.date_registered
            user.save()

if __name__ == '__main__':
    add_date_confirmed()
