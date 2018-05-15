from django.apps import apps

from framework.celery_tasks import app as celery_app
from website.identifiers.utils import get_doi_client


@celery_app.task(ignore_results=True)
def update_doi_metadata_on_change(target_guid, status):
    Guid = apps.get_model('osf.Guid')
    target_object = Guid.load(target_guid).referent
    if target_object.get_identifier('doi'):
        client = get_doi_client(target_object)
        if client and target_object.get_identifier('doi'):
            metadata = client.build_metadata(target_object)
            doi = client.build_doi(target_object)
            client.change_status_identifier(status, doi, metadata)
