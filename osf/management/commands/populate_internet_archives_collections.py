import json
import logging

from osf.models import RegistrationProvider
from django.core.management.base import BaseCommand
from website import settings
import requests

logger = logging.getLogger(__file__)


def create_ia_subcollection(provider, version_id, dry_run):
    provider_id = f"osf-registration-providers-{provider._id}-{version_id}"
    resp = None
    if not dry_run:
        resp = requests.put(
            f"https://s3.us.archive.org/{provider_id}",
            headers={
                "Authorization": f"LOW {settings.IA_ACCESS_KEY}:{settings.IA_SECRET_KEY}",
                "x-archive-meta01-title": provider.name,
                "x-archive-meta02-collection": settings.IA_ROOT_COLLECTION,
                "x-archive-meta03-mediatype": "collection",
            },
        )
    logger.info(
        f'{"DRY_RUN" if dry_run else ""} collection for {provider_id} requested with {resp}'
    )
    return resp


def update_ia_subcollection(provider, version_id, dry_run):
    provider_id = f"osf-registration-providers-{provider._id}-{version_id}"
    if not dry_run:
        # The following uses the json patch syntax more info here:
        # https://archive.org/services/docs/api/metadata.html
        changes = [
            {
                "target": "metadata",
                "patch": {
                    "op": "replace",
                    "path": "/title",
                    "value": provider.name,
                },
            },
        ]
        resp = requests.post(
            f"http://archive.org/metadata/{provider_id}",
            headers={
                "Authorization": f"LOW {settings.IA_ACCESS_KEY}:{settings.IA_SECRET_KEY}",
            },
            data={
                "target": "metadata",
                "-changes": json.dumps(changes),
                "priority": None,
            },
        )
    logger.info(
        f'{"DRY_RUN" if dry_run else ""} collection for {provider_id} updated with {resp}'
    )


def populate_internet_archives_collections(version_id, dry_run=False):
    for provider in RegistrationProvider.objects.all():
        resp = create_ia_subcollection(provider, version_id, dry_run)
        if resp.status_code == 409:
            update_ia_subcollection(provider, version_id, dry_run)


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
        version_id = options.get("version_id", settings.ID_VERSION)
        populate_internet_archives_collections(version_id, dry_run=dry_run)
