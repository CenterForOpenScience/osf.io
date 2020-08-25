# -*- coding: utf-8 -*-

"""
A management command to sync the bibliographic status of specified registration creators

i.e. docker-compose run --rm web python3 manage.py sync_registration_creator_bibliographic_status --registrations eknph wfze4 2wk4h
"""

from django.core.management.base import BaseCommand

from osf.models import Registration


def sync_registration_creator_bibliographic_status(registration_guid):
    registration = Registration.load(registration_guid)
    creator = registration.creator
    creator_contributor_reg = registration.contributor_set.get(user=creator)
    creator_contributor_node = registration.registered_from.contributor_set.get(user=creator)

    creator_contributor_reg.visible = creator_contributor_node.visible
    creator_contributor_reg.save()


class Command(BaseCommand):

    def add_arguments(self, parser):
        super(Command, self).add_arguments(parser)
        parser.add_argument(
            '--registrations',
            nargs='+',
            dest='registration_guids',
            help='Registrations to sync the initiator contributor settings for'
        )

    def handle(self, *args, **options):
        registration_guids = options.get('registration_guids')
        for registration_guid in registration_guids:
            sync_registration_creator_bibliographic_status(registration_guid)
