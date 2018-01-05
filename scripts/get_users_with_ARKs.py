# -*- coding: utf-8 -*-
import io
import csv
import logging

from website.app import setup_django
setup_django()

from website import mails
from website import settings

from osf.models import OSFUser

logger = logging.getLogger(__name__)


def find_ark_dict():
    users = OSFUser.objects.filter(nodes__identifiers__category='ark')

    users_and_guids = {}

    for user in users:
        if user.is_registered:
            users_and_guids[user.username] = list(
                user.nodes.filter(
                    is_deleted=False,
                    is_public=True,
                    identifiers__category='ark',
                )
            )

    return users_and_guids

def get_node_urls(node_list):
    urls = ''
    for node in node_list:
        urls += node.absolute_url + ', '
    return urls[0:-2]


def main():
    ark_dict = find_ark_dict()
    if ark_dict:
        filename = 'users_ark_nodes.csv'

        output = io.BytesIO()
        writer = csv.writer(output)
        for user in ark_dict:
            urls = get_node_urls(ark_dict[user])
            writer.writerow([user, urls])

        mails.send_mail(
            mail=mails.EMPTY,
            subject='Users/Projects with ARKs',
            to_addr=settings.OSF_SUPPORT_EMAIL,
            body='CSV with users/nodes with ARKs attached.',
            attachment_name=filename,
            attachment_content=output.getvalue(),
        )

    logger.info('{n} users with ARKs found.'.format(n=len(ark_dict)))
    logger.info('ARK csv email sent.')

if __name__ == '__main__':
    main()
