import json
import logging

from osf.models import RegistrationProvider
from django.core.management.base import BaseCommand
from website import settings
import requests

logger = logging.getLogger(__file__)


def populate_internet_archives_collections(version_id, dry_run=False):
    for provider in RegistrationProvider.objects.all():
        provider_id = f"osf-registration-providers-{provider._id}-{version_id}"
        if not dry_run:
            resp = requests.put(
                f"https://s3.us.archive.org/{provider_id}",
                headers={
                    "Authorization": f"LOW {settings.IA_ACCESS_KEY}:{settings.IA_SECRET_KEY}",
                    "x-archive-meta01-title": provider.name,
                    "x-archive-meta02-collection": settings.IA_ROOT_COLLECTION,
                },
            )
            if resp.status_code == 409:
                # The following uses the json patch syntax more info here:
                # https://archive.org/services/docs/api/metadata.html
                changes = [
                    {
                        "target": provider_id,
                        "patch": {
                            "op": "replace",
                            "path": "/title",
                            "value": provider.name,
                        },
                    },
                ]
                requests.post(
                    f"http://archive.org/metadata/{provider_id}",
                    headers={
                        "Authorization": f"LOW {settings.IA_ACCESS_KEY}:{settings.IA_SECRET_KEY}",
                    },
                    data={
                        "target": 'metadata',
                        "-changes": json.dumps(changes),
                        "priority": None,
                    },
                ).raise_for_status()

        logger.info(
            f'{"DRY_RUN" if dry_run else ""} collection for {provider._id} collection created with id {provider_id} '
        )


class Command(BaseCommand):
    help = """
    This command populates internet archive with subcollections for our registrations are to go in. `version_id` here
     can indicate the sequential version_id such as `v1`, or the testing environment `staging_v1`.
     """

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            "--dry",
            action="store_true",
            dest="dry_run",
            help="makes everything but logging a no-op",
        )
        parser.add_argument(
            "--version_id",
            dest="version_id",
            help="indicates the sequential version_id such as `v1`, or the testing environment `staging_v1`.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        version_id = options.get("version_id", settings.IA_ID_VERSION)
        populate_internet_archives_collections(version_id, dry_run=dry_run)
