# -*- coding: utf-8 -*-
import logging

from django.core.management.base import BaseCommand
from osf.models import Institution

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """A new permissions group was created for Institutions, which will be created upon each new Institution,
    but the old institutions will not have this group. This management command creates those groups for the
    existing institutions.
    """

    def handle(self, *args, **options):
        institutions = Institution.objects.all()
        for institution in institutions:
            institution.update_group_permissions()
            logger.info('Added perms to {}.'.format(institution.name))
