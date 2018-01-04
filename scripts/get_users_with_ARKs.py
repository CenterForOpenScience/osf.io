# -*- coding: utf-8 -*-
import io
import csv
import logging

from website.app import setup_django
setup_django()

from website import mails
from website import settings

from osf.models import AbstractNode

logger = logging.getLogger(__name__)


def find_users_with_arks():
    return list(
        AbstractNode.objects.filter(
        is_deleted=False,
        is_public=True,
        identifiers__category='ark',
        ).values_list(
            'contributor__user__username', flat=True
        ).distinct()
    )

def main():
    users_with_arks = find_users_with_arks()
    if users_with_arks:
        filename = 'users_with_arks.csv'

        output = io.BytesIO()
        writer = csv.writer(output)
        for user in users_with_arks:
            writer.writerow([user])

        mails.send_mail(
            mail=mails.EMPTY,
            subject='Users with fake ARKs',
            to_addr=settings.OSF_SUPPORT_EMAIL,
            body='List of users with ARKs attached.',
            attachment_name=filename,
            attachment_content=output.getvalue(),
        )

    logger.info('{n} users with ARKs found.'.format(n=len(users_with_arks)))
    logger.info('Users with ARKs email sent.')

if __name__ == '__main__':
    main()
