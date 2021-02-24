#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.core.management.base import BaseCommand
from osf.models import Registration


def sync_datacite_doi_metadata(dry_run=True):
    for registration in Registration.objects.all():
        if not dry_run:
            doi = registration.update_identifier('doi')['doi']
            registration.set_identifier_value('doi', doi)


class Command(BaseCommand):
    """Adds DOIs to all registrations"""
    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            '--dry',
            action='store_true',
            dest='dry_run',
        )

    def handle(self, *args, **options):
        dry_run = options.get('dry_run')
        sync_datacite_doi_metadata(dry_run=dry_run)
