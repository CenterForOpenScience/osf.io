# -*- coding: utf-8 -*-
import logging

from django.core.management.base import BaseCommand
from addons.s3.utils import update_folder_names, reverse_update_folder_names

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    Adds Colon (':') delineators to s3 buckets to separate them from them from their subfolder, so `<bucket_name>`
    becomes `<bucket_name>:/` , the root path. Folder names will also be updated to maintain consistency.

    """

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            '--reverse',
            action='store_true',
            dest='reverse',
            help='Unsets date_retraction'
        )

    def handle(self, *args, **options):
        reverse = options.get('reverse', False)
        if reverse:
            reverse_update_folder_names()
        else:
            update_folder_names()