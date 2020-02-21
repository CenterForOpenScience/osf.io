# -*- coding: utf-8 -*-
import logging

from django.core.management.base import BaseCommand
from osf.models import Institution

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """Add egap-registration schema to the db.
    For now, doing this outside of a migration so it can be individually added to
    a staging environment for preview.
    """

    def handle(self, *args, **options):
        institutions = Institution.objects.all()
        for institution in institutions:
            institution.update_group_permissions()
            logger.info('Added perms to {}.'.format(institution.name))
