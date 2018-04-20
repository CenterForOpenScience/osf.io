from django.apps import apps

from framework.celery_tasks import app as celery_app
from website import settings
from website.identifiers.utils import get_ezid_client, build_ezid_metadata, get_datacite_client, build_datacite_metadata


@celery_app.task(ignore_results=True)
def update_ezid_metadata_on_change(target_guid, status):
    Guid = apps.get_model('osf.Guid')
    target_object = Guid.load(target_guid).referent
    if (settings.EZID_USERNAME and settings.EZID_PASSWORD) and target_object.get_identifier('doi'):
        client = get_ezid_client()

        doi, metadata = build_ezid_metadata(target_object)
        client.change_status_identifier(status, doi, metadata)


@celery_app.task(ignore_results=True)
def update_datacite_metadata_on_change(target_guid, status):
    Guid = apps.get_model('osf.Guid')
    target_object = Guid.load(target_guid).referent
    if (settings.DATACITE_USERNAME and settings.DATACITE_PASSWORD) and target_object.get_identifier('doi'):
        client = get_datacite_client()

        metadata = build_datacite_metadata(target_object)
        client.metadata_post(metadata)
