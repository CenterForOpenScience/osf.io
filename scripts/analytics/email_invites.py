# -*- coding: utf-8 -*-

import os
import matplotlib.pyplot as plt

from framework.mongo import database
from website import settings

from utils import plot_dates, mkdirp


user_collection = database['user']

FIG_PATH = os.path.join(settings.ANALYTICS_PATH, 'figs', 'features')
mkdirp(FIG_PATH)


def analyze_email_invites():
    invited = user_collection.find({'unclaimed_records': {'$ne': {}}})
    dates_invited = [
        user['date_registered']
        for user in invited
    ]
    if not dates_invited:
        return
    fig = plot_dates(dates_invited)
    plt.title('email invitations ({}) total)'.format(len(dates_invited)))
    plt.savefig(os.path.join(FIG_PATH, 'email-invites.png'))
    plt.close()


def analyze_email_confirmations():
    confirmed = user_collection.find({
        'unclaimed_records': {'$ne': {}},
        'is_claimed': True,
    })
    dates_confirmed = [
        user['date_confirmed']
        for user in confirmed
    ]
    if not dates_confirmed:
        return
    fig = plot_dates(dates_confirmed)
    plt.title('confirmed email invitations ({}) total)'.format(len(dates_confirmed)))
    plt.savefig(os.path.join(FIG_PATH, 'email-invite-confirmations.png'))
    plt.close()


def main():
    analyze_email_invites()
    analyze_email_confirmations()


if __name__ == '__main__':
    main()

