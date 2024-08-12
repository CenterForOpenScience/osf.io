import logging

from django.core.management.base import BaseCommand
from django.db import transaction
from osf.models import Node, NodeLog
from framework.celery_tasks import app as celery_app
from urllib.parse import urljoin
from website import settings

logger = logging.getLogger(__name__)


def swap_guid(url, node):
    url = url.split("/")[:-1]
    url[2] = node._id
    url = "/".join(url)
    return f"{url}/?pid={node._id}"


def swap_guid_view_download(url, node):
    url = url.split("/")[:-1]
    url[1] = node._id
    url = "/".join(url)
    url = url.partition("?pid=")[0] + f"/?pid={node._id}"
    return url


error_causing_log_actions = {
    "addon_file_renamed",
    "addon_file_moved",
    "addon_file_copied",
}

dead_links_actions = {
    "osf_storage_file_added",
    "file_tag_removed",
    "file_tag_added",
    "osf_storage_file_removed",
    "osf_storage_file_updated",
}

affected_log_actions = error_causing_log_actions.union(dead_links_actions)


@celery_app.task(
    name="osf.management.commands.fix_quickfiles_waterbutler_logs"
)
def fix_logs(node_id, dry_run=False):
    """
    Fixes view/download links for waterbutler based file logs, and also fixes old 10 digit node params for moved/renamed
    files.
    """
    logger.info(f"{node_id} Quickfiles logs started")

    with transaction.atomic():
        logger.debug(f"{node_id} Quickfiles logs started")

        node = Node.load(node_id)
        for log in node.logs.filter(action__in=error_causing_log_actions):
            log.params["params_node"] = {"_id": node._id, "title": node.title}
            if log.params.get("auth"):
                log.params["auth"]["callback_url"] = urljoin(
                    settings.DOMAIN,
                    f"project/{node_id}/node/{node_id}/waterbutler/logs/",
                )

            url = swap_guid(log.params["source"]["url"], node)

            if (
                log.params["source"]["resource"]
                == log.params["destination"]["resource"]
            ):
                log.params["source"]["url"] = url
                log.params["source"]["nid"] = node._id
                if log.params["source"].get("node"):
                    log.params["source"]["node"]["url"] = f"/{node._id}/"
                    log.params["source"]["node"]["_id"] = node._id
                if log.params["source"].get("resource"):
                    log.params["source"]["resource"] = node._id

            log.params["destination"]["url"] = url
            log.params["destination"]["nid"] = node._id

            if log.params["destination"].get("node"):
                log.params["destination"]["node"]["url"] = f"/{node._id}/"
                log.params["destination"]["node"]["_id"] = node._id

            if log.params["destination"].get("resource"):
                log.params["destination"]["resource"] = node._id

            if log.params.get("urls"):
                url = swap_guid_view_download(log.params["urls"]["view"], node)
                log.params["urls"] = {
                    "view": url,
                    "download": f"{url}&action=download",
                }

            log.save()

        for log in node.logs.filter(action__in=dead_links_actions):
            log.params["params_node"] = {"_id": node._id, "title": node.title}

            url = swap_guid_view_download(log.params["urls"]["view"], node)

            log.params["urls"] = {
                "view": url,
                "download": f"{url}&action=download",
            }
            log.save()

        node.save()
        if dry_run:
            raise RuntimeError("This was a dry run.")

    logger.info(f"{node._id} Quickfiles logs fixed")


def fix_quickfiles_waterbutler_logs(dry_run=False):
    nodes = Node.objects.filter(
        logs__action=NodeLog.MIGRATED_QUICK_FILES
    ).values_list("guids___id", flat=True)
    logger.info(f"{nodes.count()} Quickfiles nodes with bugged logs found.")

    for node_id in nodes:
        logger.info(f"{node_id} Quickfiles logs fixing started")
        fix_logs.apply_async(args=(node_id,), kwargs={"dry_run": dry_run})


class Command(BaseCommand):
    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            "--dry",
            action="store_true",
            dest="dry_run",
            help="Dry run",
        )

    def handle(self, *args, **options):
        dry_run = options.get("dry_run")
        fix_quickfiles_waterbutler_logs(dry_run=dry_run)
